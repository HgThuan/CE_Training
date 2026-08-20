import json
from decimal import Decimal
from unittest.mock import Mock, patch

import pytest
from django.core.cache import cache
from django.test import override_settings

from apps.ai.models import EMBEDDING_DIMENSIONS, AIRequestLog
from apps.ai.providers import (
    AIProviderError,
    BaseAIProvider,
    EmbeddingResponse,
    GeminiProvider,
    ProviderResponse,
)
from apps.ai.services import AI_CACHE_PAYLOAD_VERSION, AIService


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield
    cache.clear()


def provider_mock() -> Mock:
    provider = Mock(spec=BaseAIProvider)
    provider.name = "gemini"
    return provider


@pytest.mark.django_db
@override_settings(
    AI_FEATURES_ENABLED=True,
    AI_MAX_RETRIES=0,
    AI_INPUT_COST_PER_MILLION="1.5",
    AI_OUTPUT_COST_PER_MILLION="3",
)
def test_generate_text_logs_usage_cost_and_passes_timeout_and_schema():
    provider = provider_mock()
    provider.generate_text.return_value = ProviderResponse(
        text='{"keywords":["điện thoại"]}',
        input_tokens=1_000,
        output_tokens=500,
        metadata={"finish_reason": "STOP"},
    )
    service = AIService(provider=provider, monotonic_fn=Mock(side_effect=[1.0, 1.125]))

    result = service.generate_text(
        feature=AIRequestLog.Feature.SMART_SEARCH,
        prompt="điện thoại tốt",
        response_mime_type="application/json",
        response_schema={"type": "object"},
        cache_ttl=0,
    )

    assert result.ai_used is True
    assert result.fallback_used is False
    provider.generate_text.assert_called_once()
    kwargs = provider.generate_text.call_args.kwargs
    assert kwargs["timeout"] > 0
    assert kwargs["response_schema"] == {"type": "object"}
    log = AIRequestLog.objects.get()
    assert log.status == AIRequestLog.Status.SUCCESS
    assert log.latency_ms == 125
    assert log.input_tokens == 1_000
    assert log.output_tokens == 500
    assert log.estimated_cost == Decimal("0.003000")


@pytest.mark.django_db
@override_settings(
    AI_FEATURES_ENABLED=True,
    AI_MAX_RETRIES=2,
    AI_RETRY_BACKOFF_SECONDS=0.1,
)
def test_generate_text_retries_retryable_provider_errors_with_exponential_backoff():
    provider = provider_mock()
    provider.generate_text.side_effect = [
        AIProviderError("busy", code="http_503"),
        AIProviderError("busy", code="http_503"),
        ProviderResponse(text="ok"),
    ]
    sleeps: list[float] = []

    result = AIService(provider=provider, sleep_fn=sleeps.append).generate_text(
        feature="other",
        prompt="retry",
        cache_ttl=0,
    )

    assert result.text == "ok"
    assert provider.generate_text.call_count == 3
    assert sleeps == [0.1, 0.2]
    assert AIRequestLog.objects.get().metadata["attempts"] == 3


@pytest.mark.django_db
@override_settings(AI_FEATURES_ENABLED=True, AI_MAX_RETRIES=5)
def test_generate_text_does_not_retry_programming_errors_and_uses_fallback():
    provider = provider_mock()
    provider.generate_text.side_effect = TypeError("bad integration")

    result = AIService(provider=provider, sleep_fn=Mock()).generate_text(
        feature="other",
        prompt="safe fallback",
        fallback="keyword result",
        cache_ttl=0,
    )

    assert result.text == "keyword result"
    assert result.ai_used is False
    assert result.fallback_used is True
    provider.generate_text.assert_called_once()
    log = AIRequestLog.objects.get()
    assert log.status == AIRequestLog.Status.FALLBACK
    assert log.metadata["attempts"] == 1


@pytest.mark.django_db
@override_settings(AI_FEATURES_ENABLED=True, AI_MAX_RETRIES=0)
def test_generate_text_uses_deterministic_cache_and_logs_cache_hits():
    provider = provider_mock()
    provider.generate_text.return_value = ProviderResponse(text="cached answer")
    service = AIService(provider=provider)
    kwargs = {
        "feature": "other",
        "prompt": "stable prompt",
        "cache_context": {"b": 2, "a": 1},
    }

    first = service.generate_text(**kwargs)
    second = service.generate_text(**kwargs)

    assert first.cached is False
    assert second.cached is True
    assert second.text == "cached answer"
    provider.generate_text.assert_called_once()
    assert list(
        AIRequestLog.objects.order_by("created_at").values_list(
            "status",
            flat=True,
        )
    ) == [AIRequestLog.Status.SUCCESS, AIRequestLog.Status.CACHED]


@pytest.mark.django_db
@override_settings(AI_FEATURES_ENABLED=True, AI_MAX_RETRIES=0)
def test_global_kill_switch_is_checked_before_a_cached_ai_result():
    provider = provider_mock()
    provider.generate_text.return_value = ProviderResponse(text="ai answer")
    service = AIService(provider=provider)
    kwargs = {"feature": "other", "prompt": "kill switch"}
    service.generate_text(**kwargs)

    with override_settings(AI_FEATURES_ENABLED=False):
        result = service.generate_text(**kwargs, fallback="fallback")

    assert result.text == "fallback"
    assert result.ai_used is False
    assert result.cached is False
    provider.generate_text.assert_called_once()
    assert AIRequestLog.objects.order_by("-created_at").first().error_code == ("feature_disabled")


@pytest.mark.django_db
@override_settings(AI_FEATURES_ENABLED=True, AI_MAX_RETRIES=0)
@pytest.mark.parametrize(
    "malformed",
    [
        {
            "version": AI_CACHE_PAYLOAD_VERSION,
            "kind": "text",
            "model_name": "gemini-3.6-flash",
            "text": "bad",
            "input_tokens": "not-an-int",
            "output_tokens": 0,
            "metadata": {},
        },
        {
            "version": AI_CACHE_PAYLOAD_VERSION,
            "kind": "text",
            "model_name": "gemini-3.6-flash",
            "text": "bad",
            "input_tokens": 0,
            "output_tokens": 0,
            "metadata": "not-an-object",
        },
    ],
)
def test_malformed_cache_entries_are_treated_as_cache_misses(malformed):
    provider = provider_mock()
    provider.generate_text.return_value = ProviderResponse(text="fresh")

    with patch("apps.ai.services.safe_cache_get", return_value=malformed):
        result = AIService(provider=provider).generate_text(
            feature="other",
            prompt="malformed cache",
        )

    assert result.text == "fresh"
    assert result.cached is False
    provider.generate_text.assert_called_once()


@pytest.mark.django_db
@override_settings(AI_FEATURES_ENABLED=True, AI_MAX_RETRIES=0)
def test_embedding_validates_dimensions_caches_and_logs_without_vector_payload():
    provider = provider_mock()
    provider.embed_text.return_value = EmbeddingResponse(
        vector=[0.25] * EMBEDDING_DIMENSIONS,
        input_tokens=12,
    )
    service = AIService(provider=provider)

    first = service.get_embedding(
        feature=AIRequestLog.Feature.EMBEDDING,
        text="camera chống nước",
        task_type="retrieval_query",
    )
    second = service.get_embedding(
        feature=AIRequestLog.Feature.EMBEDDING,
        text="camera chống nước",
        task_type="retrieval_query",
    )

    assert len(first.vector) == EMBEDDING_DIMENSIONS
    assert first.ai_used is True
    assert second.cached is True
    provider.embed_text.assert_called_once()
    logs = AIRequestLog.objects.order_by("created_at")
    assert logs[0].prompt.startswith("task: search result | query:")
    assert "vector" not in logs[0].metadata


@pytest.mark.django_db
@override_settings(AI_FEATURES_ENABLED=True, AI_MAX_RETRIES=0)
def test_embedding_with_wrong_dimensions_degrades_to_empty_fallback():
    provider = provider_mock()
    provider.embed_text.return_value = EmbeddingResponse(vector=[0.1])

    result = AIService(provider=provider).get_embedding(
        feature=AIRequestLog.Feature.EMBEDDING,
        text="product",
        task_type="retrieval_document",
        title="Title",
        fallback=[1.0],
        cache_ttl=0,
    )

    assert result.vector == []
    assert result.ai_used is False
    assert result.fallback_used is True
    assert AIRequestLog.objects.get().error_code == "invalid_dimensions"


@pytest.mark.django_db
@override_settings(AI_FEATURES_ENABLED=True, AI_MAX_RETRIES=0)
def test_extract_search_intent_returns_safe_shape_and_rejects_non_finite_filters():
    provider = provider_mock()
    provider.generate_text.return_value = ProviderResponse(
        text=json.dumps(
            {
                "keywords": ["điện thoại", 42, "x" * 150],
                "filters": {
                    "price_max": "NaN",
                    "price_min": 1_000_000,
                    "unknown": "ignored",
                    "in_stock": True,
                },
                "explanation": "Phù hợp nhu cầu",
            },
            ensure_ascii=False,
        )
    )

    intent = AIService(provider=provider).extract_search_intent("điện thoại dưới 5 triệu")

    assert intent["keywords"] == ["điện thoại", "x" * 100]
    assert intent["filters"] == {"price_min": 1_000_000, "in_stock": True}
    assert intent["ai_used"] is True
    assert intent["fallback_used"] is False


@pytest.mark.django_db
@override_settings(AI_FEATURES_ENABLED=True, AI_MAX_RETRIES=0)
def test_invalid_intent_json_returns_keyword_and_price_fallback():
    provider = provider_mock()
    provider.generate_text.return_value = ProviderResponse(text="not json")

    intent = AIService(provider=provider).extract_search_intent("điện thoại dưới 5 triệu")

    assert intent["ai_used"] is False
    assert intent["fallback_used"] is True
    assert intent["filters"]["price_max"] == 5_000_000
    assert "điện" in intent["keywords"]


def test_gemini_generation_uses_current_structured_output_payload():
    provider = GeminiProvider(api_key="test-only")
    response = {
        "candidates": [
            {
                "content": {"parts": [{"text": '{"ok":true}'}]},
                "finishReason": "STOP",
            }
        ],
        "usageMetadata": {"promptTokenCount": 3, "candidatesTokenCount": 2},
    }
    schema = {"type": "object", "properties": {"ok": {"type": "boolean"}}}

    with patch.object(provider, "_post_json", return_value=response) as post_json:
        result = provider.generate_text(
            prompt="return json",
            model_name="gemini-3.6-flash",
            timeout=2,
            response_mime_type="application/json",
            response_schema=schema,
        )

    payload = post_json.call_args.args[1]
    assert payload["generationConfig"]["responseFormat"] == {
        "text": {"mimeType": "APPLICATION_JSON", "schema": schema}
    }
    assert payload["generationConfig"]["thinkingConfig"] == {"thinkingLevel": "minimal"}
    assert "responseMimeType" not in payload["generationConfig"]
    assert result.input_tokens == 3
    assert result.output_tokens == 2


def test_gemini_chat_stream_preserves_function_call_contract():
    provider = GeminiProvider(api_key="test-only")
    stream = [
        {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {"text": "Mình sẽ tìm ngay. "},
                            {
                                "functionCall": {
                                    "id": "call-1",
                                    "name": "search_products",
                                    "args": {"query": "laptop học tập"},
                                },
                                "thoughtSignature": "signed-thought",
                            },
                        ]
                    },
                    "finishReason": "STOP",
                }
            ],
            "usageMetadata": {"promptTokenCount": 8, "candidatesTokenCount": 5},
        }
    ]
    tool = {
        "name": "search_products",
        "description": "Tìm sản phẩm",
        "parameters": {"type": "object"},
    }
    messages = [
        {"role": "system", "content": "Tóm tắt cũ"},
        {"role": "user", "content": "Tìm laptop"},
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "id": "previous-call",
                    "name": "get_policy",
                    "arguments": {"topic": "đổi trả"},
                    "thought_signature": "previous-signature",
                }
            ],
        },
        {
            "role": "tool",
            "name": "get_policy",
            "tool_call_id": "previous-call",
            "content": '{"documents": []}',
        },
    ]

    with patch.object(provider, "_stream_json", return_value=iter(stream)) as stream_json:
        chunks = list(
            provider.generate_chat(
                messages=messages,
                tools=[tool],
                system_prompt="Trợ lý mua sắm",
                model_name="gemini-3.6-flash",
                timeout=5,
            )
        )

    url, payload = stream_json.call_args.args[:2]
    assert url.endswith(":streamGenerateContent?alt=sse")
    assert payload["tools"] == [{"functionDeclarations": [tool]}]
    assert payload["systemInstruction"]["parts"][0]["text"] == ("Trợ lý mua sắm\n\nTóm tắt cũ")
    assert payload["contents"][1]["parts"][0] == {
        "functionCall": {
            "name": "get_policy",
            "args": {"topic": "đổi trả"},
            "id": "previous-call",
        },
        "thoughtSignature": "previous-signature",
    }
    assert payload["contents"][2]["parts"][0]["functionResponse"] == {
        "name": "get_policy",
        "response": {"documents": []},
        "id": "previous-call",
    }
    assert chunks[0].delta_text == "Mình sẽ tìm ngay. "
    assert chunks[0].input_tokens == 8
    assert chunks[0].output_tokens == 5
    assert chunks[0].tool_calls[0].id == "call-1"
    assert chunks[0].tool_calls[0].name == "search_products"
    assert chunks[0].tool_calls[0].arguments == {"query": "laptop học tập"}
    assert chunks[0].tool_calls[0].thought_signature == "signed-thought"


@pytest.mark.parametrize(
    ("model_name", "expected_config"),
    [
        (
            "gemini-embedding-2",
            {"outputDimensionality": EMBEDDING_DIMENSIONS},
        ),
        (
            "gemini-embedding-001",
            {
                "outputDimensionality": EMBEDDING_DIMENSIONS,
                "taskType": "RETRIEVAL_DOCUMENT",
                "title": "Áo mưa",
            },
        ),
    ],
)
def test_gemini_embedding_payload_uses_config_and_document_prefix(
    model_name,
    expected_config,
):
    provider = GeminiProvider(api_key="test-only")
    response = {"embedding": {"values": [0.0] * EMBEDDING_DIMENSIONS}}

    with patch.object(provider, "_post_json", return_value=response) as post_json:
        provider.embed_text(
            text="Chống nước tốt",
            task_type="retrieval_document",
            title="Áo mưa",
            model_name=model_name,
            dimensions=EMBEDDING_DIMENSIONS,
            timeout=2,
        )

    payload = post_json.call_args.args[1]
    assert payload["content"]["parts"][0]["text"] == ("title: Áo mưa | text: Chống nước tốt")
    assert payload["embedContentConfig"] == expected_config
    assert "taskType" not in payload
    assert "title" not in payload
    assert "outputDimensionality" not in payload


@override_settings(AI_FEATURES_ENABLED=True, GEMINI_API_KEY="configured")
def test_ai_service_configuration_check_never_exposes_key():
    assert AIService.is_configured() is True

    with override_settings(GEMINI_API_KEY=""):
        assert AIService.is_configured() is False
