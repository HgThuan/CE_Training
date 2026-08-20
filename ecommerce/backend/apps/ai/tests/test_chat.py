import json
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest
from django.conf import settings
from django.core.cache import cache
from django.test import override_settings
from rest_framework.test import APIClient

from apps.account.models import User
from apps.ai.chat_service import AIChatService, ChatEvent
from apps.ai.models import AIRequestLog, ChatMessage, ChatSession, PolicyDocument
from apps.ai.providers import AIProviderError, BaseAIProvider, ChatChunk, ToolCall
from apps.ai.providers.gemini import GeminiProvider
from apps.ai.services import AIResult, AIService
from apps.ai.tools import _get_policy, _serialize_products_with_verified_ratings
from apps.catalog.tests.factories import CategoryFactory
from apps.product.models import Product
from apps.product.tests.factories import ProductFactory


def product_payload(product_id=None):
    return {
        "id": str(product_id or uuid4()),
        "name": "Laptop học tập",
        "slug": "laptop-hoc-tap",
        "thumbnail": None,
        "min_price": "15990000",
        "max_price": "15990000",
        "regular_min_price": "15990000",
        "regular_max_price": "15990000",
        "is_flash_sale": False,
        "flash_sale_ends_at": None,
        "rating_average": "4.80",
        "rating_count": 12,
        "sold_count": 8,
        "shop_name": "Mercato Tech",
        "shop_slug": "mercato-tech",
    }


def product_search_result(product, *, kind="exact", missing_terms=None):
    return {
        "products": [product],
        "result_count": 1,
        "matches": [
            {
                "product_id": product["id"],
                "kind": kind,
                "matched_terms": ["laptop"] if kind == "exact" else ["dong", "ho"],
                "missing_terms": missing_terms or [],
            }
        ],
    }


def fake_provider(*rounds):
    provider = Mock(spec=BaseAIProvider)
    provider.name = "gemini"
    provider.generate_chat.side_effect = [iter(round_chunks) for round_chunks in rounds]
    return provider


@pytest.fixture(autouse=True)
def clear_throttle_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.mark.django_db
def test_chat_turn_grounds_product_card_from_search_result():
    product = product_payload()
    provider = fake_provider(
        [
            ChatChunk(
                tool_calls=[
                    ToolCall(
                        id="search-1",
                        name="search_products",
                        arguments={"query": "laptop học tập"},
                    )
                ]
            )
        ],
        [ChatChunk(delta_text="Mình tìm thấy một lựa chọn phù hợp.")],
    )
    executor = Mock(return_value=product_search_result(product))
    session = ChatSession.objects.create(guest_token="guest-token-for-chat-tests")

    events = list(
        AIChatService(provider=provider, tool_executor=executor).handle_turn(
            session,
            "Tìm laptop học tập",
        )
    )

    done = events[-1].to_dict()["message"]
    assert done["content"] == (
        "Mình tìm thấy 1 sản phẩm khớp với những tiêu chí có thể kiểm chứng từ dữ liệu Mercato."
    )
    assert done["attachments"] == [
        {
            "type": "product_card",
            "product_id": product["id"],
            "product": product,
            "match": product_search_result(product)["matches"][0],
        }
    ]
    assert ChatMessage.objects.filter(session=session, role=ChatMessage.Role.TOOL).count() == 1
    assert AIRequestLog.objects.get(feature=AIRequestLog.Feature.CHAT_TURN).metadata[
        "tool_names"
    ] == ["search_products"]


@pytest.mark.django_db
def test_gift_advice_asks_for_missing_needs_before_searching():
    CategoryFactory(name="Âm thanh", slug="am-thanh")
    provider = fake_provider([ChatChunk(delta_text="Không được gọi")])
    executor = Mock()
    session = ChatSession.objects.create(guest_token="guest-token-gift-clarification")

    events = list(
        AIChatService(provider=provider, tool_executor=executor).handle_turn(
            session,
            "Tôi muốn mua quà sinh nhật cho bạn",
        )
    )

    response = events[-1].message["content"]
    assert "Bạn ấy thích gì" in response
    assert "Ngân sách dự kiến" in response
    assert events[-1].message["attachments"] == []
    provider.generate_chat.assert_not_called()
    executor.assert_not_called()
    request_log = AIRequestLog.objects.get(feature=AIRequestLog.Feature.CHAT_TURN)
    assert request_log.provider == "dialogue_rules"
    assert request_log.metadata["dialogue_action"] == "clarify"
    assert request_log.metadata["dialogue_intent"] == "gift_advice"


@pytest.mark.django_db
def test_gift_advice_does_not_invent_a_birthday_for_other_occasions():
    session = ChatSession.objects.create(guest_token="guest-token-wedding-gift")

    events = list(
        AIChatService(provider=fake_provider()).handle_turn(
            session,
            "Tôi muốn mua quà cưới cho bạn",
        )
    )

    assert "chọn quà đám cưới" in events[-1].message["content"]
    assert "sinh nhật" not in events[-1].message["content"]


@pytest.mark.django_db
def test_gift_advice_understands_standalone_budget_follow_up():
    CategoryFactory(name="Âm thanh", slug="am-thanh")
    provider = fake_provider([ChatChunk(delta_text="Không được gọi")])
    executor = Mock()
    session = ChatSession.objects.create(guest_token="guest-token-standalone-budget")
    service = AIChatService(provider=provider, tool_executor=executor)

    list(service.handle_turn(session, "Tôi muốn mua quà sinh nhật"))
    events = list(service.handle_turn(session, "1 triệu"))

    assert "ngân sách khoảng 1.000.000 đ" in events[-1].message["content"]
    assert "Người nhận thích gì" in events[-1].message["content"]
    provider.generate_chat.assert_not_called()
    executor.assert_not_called()


@pytest.mark.django_db
def test_gift_advice_collects_slots_across_turns_then_runs_grounded_search():
    CategoryFactory(name="Âm thanh", slug="am-thanh")
    CategoryFactory(name="Phụ kiện", slug="phu-kien")
    CategoryFactory(name="Thiết bị đeo", slug="thiet-bi-deo")
    product = product_payload()
    provider = fake_provider([ChatChunk(delta_text="Không được gọi")])
    executor = Mock(return_value=product_search_result(product))
    session = ChatSession.objects.create(guest_token="guest-token-gift-multiturn")
    service = AIChatService(provider=provider, tool_executor=executor)

    first = list(service.handle_turn(session, "Tôi muốn mua quà sinh nhật cho bạn"))
    second = list(service.handle_turn(session, "Bạn ấy thích công nghệ, tầm 1 triệu"))
    third = list(service.handle_turn(session, "Âm thanh"))

    assert "Bạn ấy thích gì" in first[-1].message["content"]
    assert "sở thích công nghệ" in second[-1].message["content"]
    assert "Âm thanh, Phụ kiện hay Thiết bị đeo" in second[-1].message["content"]
    assert third[-1].message["attachments"][0]["product_id"] == product["id"]
    assert "Mình tìm thấy 1 sản phẩm khớp" in third[-1].message["content"]
    provider.generate_chat.assert_not_called()
    executor.assert_called_once_with(
        "search_products",
        {
            "query": "Âm thanh",
            "category": "Âm thanh",
            "limit": 4,
            "max_price": 1_000_000,
            "_user_need": "Âm thanh dưới 1000000 đồng",
        },
        user=None,
    )
    log_actions = list(
        AIRequestLog.objects.filter(feature=AIRequestLog.Feature.CHAT_TURN)
        .order_by("created_at")
        .values_list("metadata__dialogue_action", flat=True)
    )
    assert log_actions == ["clarify", "clarify", "guided_search"]


@pytest.mark.django_db
def test_gift_follow_up_can_repeat_gift_words_without_losing_collected_budget():
    CategoryFactory(name="Âm thanh", slug="am-thanh")
    executor = Mock(return_value=product_search_result(product_payload()))
    session = ChatSession.objects.create(guest_token="guest-token-gift-repeat-words")
    service = AIChatService(provider=fake_provider(), tool_executor=executor)

    list(service.handle_turn(session, "Tôi muốn mua quà sinh nhật"))
    list(service.handle_turn(session, "Ngân sách khoảng 1 triệu"))
    events = list(service.handle_turn(session, "Tôi muốn mua quà là tai nghe"))

    assert events[-1].message["attachments"]
    search_arguments = executor.call_args.args[1]
    assert search_arguments["query"] == "tai nghe"
    assert search_arguments["max_price"] == 1_000_000


@pytest.mark.django_db
def test_gift_advice_uses_latest_category_and_budget_corrections():
    CategoryFactory(name="Âm thanh", slug="am-thanh")
    CategoryFactory(name="Phụ kiện", slug="phu-kien")
    executor = Mock(return_value=product_search_result(product_payload()))
    session = ChatSession.objects.create(guest_token="guest-token-gift-correction")
    service = AIChatService(provider=fake_provider(), tool_executor=executor)

    list(service.handle_turn(session, "Tôi muốn mua quà sinh nhật"))
    list(service.handle_turn(session, "Ngân sách dưới 1 triệu"))
    events = list(service.handle_turn(session, "Đổi lên khoảng 2 triệu, chọn Phụ kiện"))

    assert events[-1].message["attachments"]
    search_arguments = executor.call_args.args[1]
    assert search_arguments["query"] == "Phụ kiện"
    assert search_arguments["category"] == "Phụ kiện"
    assert search_arguments["max_price"] == 2_000_000


@pytest.mark.django_db
def test_gift_advice_separates_over_budget_alternatives():
    CategoryFactory(name="Âm thanh", slug="am-thanh")
    product = product_payload()
    executor = Mock(
        side_effect=[
            {"products": [], "result_count": 0, "matches": []},
            product_search_result(
                product,
                kind="alternative",
                missing_terms=["budget_max:1000000"],
            ),
        ]
    )
    session = ChatSession.objects.create(guest_token="guest-token-gift-alternative")
    service = AIChatService(provider=fake_provider(), tool_executor=executor)

    list(service.handle_turn(session, "Tôi muốn mua quà sinh nhật"))
    events = list(service.handle_turn(session, "Tai nghe dưới 1 triệu"))

    assert "chưa tìm thấy sản phẩm đáp ứng đầy đủ" in events[-1].message["content"]
    assert events[-1].message["attachments"][0]["match"]["kind"] == "alternative"
    assert executor.call_count == 2
    assert executor.call_args_list[0].kwargs["user"] is None
    assert executor.call_args_list[0].args[1]["query"] == "tai nghe"
    assert executor.call_args_list[0].args[1]["category"] == "Âm thanh"
    assert executor.call_args_list[0].args[1]["_user_need"] == ("tai nghe dưới 1000000 đồng")
    assert executor.call_args_list[0].args[1]["max_price"] == 1_000_000
    assert "max_price" not in executor.call_args_list[1].args[1]


@pytest.mark.django_db
def test_gift_advice_can_be_cancelled_and_returns_to_general_chat():
    provider = fake_provider([ChatChunk(delta_text="Mình sẽ chuyển sang tìm laptop cho bạn.")])
    executor = Mock()
    session = ChatSession.objects.create(guest_token="guest-token-cancel-gift")
    service = AIChatService(provider=provider, tool_executor=executor)

    list(service.handle_turn(session, "Tôi muốn mua quà sinh nhật"))
    events = list(service.handle_turn(session, "Không mua quà nữa, tìm laptop"))

    assert events[-1].message["content"] == "Mình sẽ chuyển sang tìm laptop cho bạn."
    provider.generate_chat.assert_called_once()
    executor.assert_not_called()


@pytest.mark.django_db
def test_general_buying_advice_collects_purpose_budget_then_searches():
    CategoryFactory(name="Laptop", slug="laptop")
    CategoryFactory(name="Máy tính bảng", slug="may-tinh-bang")
    executor = Mock(return_value=product_search_result(product_payload()))
    provider = fake_provider([ChatChunk(delta_text="Không được gọi")])
    session = ChatSession.objects.create(guest_token="guest-token-general-advice")
    service = AIChatService(provider=provider, tool_executor=executor)

    first = list(service.handle_turn(session, "Gợi ý sản phẩm để học tập"))
    second = list(service.handle_turn(session, "Laptop, tầm 15 triệu"))

    assert "ưu tiên nhóm nào: Laptop hay Máy tính bảng" in first[-1].message["content"]
    assert "Ngân sách dự kiến" in first[-1].message["content"]
    assert second[-1].message["attachments"]
    provider.generate_chat.assert_not_called()
    executor.assert_called_once_with(
        "search_products",
        {
            "query": "Laptop",
            "category": "Laptop",
            "limit": 4,
            "max_price": 15_000_000,
            "_user_need": "Laptop dưới 15000000 đồng",
        },
        user=None,
    )
    latest_log = AIRequestLog.objects.order_by("-created_at").first()
    assert latest_log.metadata["dialogue_intent"] == "shopping_advice"


@pytest.mark.django_db
def test_guided_search_failure_returns_a_stable_done_event():
    CategoryFactory(name="Âm thanh", slug="am-thanh")
    executor = Mock(side_effect=RuntimeError("catalog unavailable"))
    session = ChatSession.objects.create(guest_token="guest-token-guided-search-error")

    events = list(
        AIChatService(provider=fake_provider(), tool_executor=executor).handle_turn(
            session,
            "Tôi muốn mua quà sinh nhật là tai nghe dưới 1 triệu",
        )
    )

    assert events[-1].type == "done"
    assert "đã ghi nhận đủ nhu cầu" in events[-1].message["content"]
    assert "chưa thể tra cứu danh mục Mercato" in events[-1].message["content"]
    assert executor.call_count == 1
    request_log = AIRequestLog.objects.get(feature=AIRequestLog.Feature.CHAT_TURN)
    assert request_log.status == AIRequestLog.Status.FALLBACK
    assert request_log.error_code == "guided_search_failed"


@pytest.mark.django_db
@override_settings(AI_MAX_RETRIES=1, AI_RETRY_BACKOFF_SECONDS=0.01)
def test_chat_retries_rate_limit_then_returns_grounded_response():
    provider = Mock(spec=BaseAIProvider)
    provider.name = "gemini"
    provider.generate_chat.side_effect = [
        AIProviderError("rate limited", code="http_429", retryable=True),
        iter([ChatChunk(delta_text="Mình đã tìm lại được kết quả phù hợp.")]),
    ]
    sleeps: list[float] = []
    session = ChatSession.objects.create(guest_token="guest-token-retry")

    events = list(
        AIChatService(provider=provider, sleep_fn=sleeps.append).handle_turn(
            session,
            "Tìm laptop học tập",
        )
    )

    assert provider.generate_chat.call_count == 2
    assert sleeps == [0.01]
    assert events[-1].message["content"] == "Mình đã tìm lại được kết quả phù hợp."


@pytest.mark.django_db
@override_settings(AI_MAX_RETRIES=1, AI_RETRY_BACKOFF_SECONDS=0)
def test_chat_rate_limit_falls_back_to_real_catalog_results():
    product = product_payload()
    provider = Mock(spec=BaseAIProvider)
    provider.name = "gemini"
    provider.generate_chat.side_effect = AIProviderError(
        "rate limited",
        code="http_429",
        retryable=True,
    )
    executor = Mock(return_value=product_search_result(product))
    session = ChatSession.objects.create(guest_token="guest-token-local-fallback")

    events = list(
        AIChatService(
            provider=provider,
            tool_executor=executor,
            sleep_fn=Mock(),
        ).handle_turn(session, "Tìm laptop học tập")
    )

    done = events[-1].message
    assert provider.generate_chat.call_count == 2
    assert "Mình tìm thấy 1 sản phẩm khớp" in done["content"]
    assert done["attachments"] == [
        {
            "type": "product_card",
            "product_id": product["id"],
            "product": product,
            "match": product_search_result(product)["matches"][0],
        }
    ]
    executor.assert_called_once_with(
        "search_products",
        {
            "query": "Tìm laptop học tập",
            "limit": 4,
            "_user_need": "Tìm laptop học tập",
        },
        user=None,
    )


@pytest.mark.django_db
@override_settings(AI_MAX_RETRIES=0)
def test_chat_fallback_separates_missing_request_from_alternatives():
    product = product_payload()
    provider = Mock(spec=BaseAIProvider)
    provider.name = "gemini"
    provider.generate_chat.side_effect = AIProviderError(
        "rate limited",
        code="http_429",
        retryable=True,
    )
    executor = Mock(
        side_effect=[
            {"products": [], "result_count": 0},
            {"products": [], "result_count": 0},
            {"products": [], "result_count": 0},
            product_search_result(
                product,
                kind="alternative",
                missing_terms=["chu noi braille", "khiem thi"],
            ),
        ]
    )
    session = ChatSession.objects.create(guest_token="guest-token-alternative-fallback")

    events = list(
        AIChatService(provider=provider, tool_executor=executor).handle_turn(
            session,
            "Tôi cần đồng hồ chữ nổi Braille cho người khiếm thị",
        )
    )

    done = events[-1].message
    assert "chưa tìm thấy sản phẩm đáp ứng đầy đủ" in done["content"]
    assert "chỉ gần với một phần nhu cầu" in done["content"]
    assert "không nhầm với sản phẩm phù hợp hoàn toàn" in done["content"]
    assert done["attachments"][0]["product_id"] == product["id"]
    assert executor.call_args_list[-1].args == (
        "search_products",
        {
            "query": "đồng hồ",
            "limit": 4,
            "_user_need": "Tôi cần đồng hồ chữ nổi Braille cho người khiếm thị",
        },
    )


@pytest.mark.django_db
def test_chat_hides_review_metrics_from_model_and_removes_numeric_review_claims():
    product = product_payload()
    provider = fake_provider(
        [
            ChatChunk(
                tool_calls=[
                    ToolCall(
                        id="search-with-rating",
                        name="search_products",
                        arguments={"query": "laptop"},
                    )
                ]
            )
        ],
        [
            ChatChunk(
                delta_text=(
                    "Sản phẩm này có 4.9 sao và 999 lượt đánh giá.\nMẫu này phù hợp để học tập."
                )
            )
        ],
    )
    session = ChatSession.objects.create(guest_token="guest-token-rating-grounding")

    events = list(
        AIChatService(
            provider=provider,
            tool_executor=Mock(return_value=product_search_result(product)),
        ).handle_turn(session, "Tìm laptop")
    )

    tool_context = provider.generate_chat.call_args_list[1].kwargs["messages"][-1]["content"]
    assert "rating_average" not in tool_context
    assert "rating_count" not in tool_context
    assert "4.9 sao" not in events[-1].message["content"]
    assert "999 lượt đánh giá" not in events[-1].message["content"]
    assert "Mình tìm thấy 1 sản phẩm khớp" in events[-1].message["content"]


@pytest.mark.django_db
def test_chat_product_rating_ignores_unverified_cached_product_values():
    product = ProductFactory(
        status=Product.Status.APPROVED,
        rating_average="4.95",
        rating_count=87,
    )

    serialized = _serialize_products_with_verified_ratings([product])

    assert serialized[0]["rating_average"] == "0.00"
    assert serialized[0]["rating_count"] == 0


def test_grounding_removes_unknown_product_and_compare_attachments():
    grounded_id = str(uuid4())
    unknown_id = str(uuid4())
    attachments = [
        {
            "type": "product_card",
            "product_id": grounded_id,
            "product": product_payload(grounded_id),
        },
        {
            "type": "product_card",
            "product_id": unknown_id,
            "product": product_payload(unknown_id),
        },
        {
            "type": "compare_table",
            "product_ids": [grounded_id, unknown_id],
            "comparison": {},
        },
    ]

    result = AIChatService._ground_and_deduplicate_attachments(
        attachments,
        {grounded_id},
    )

    assert result == [attachments[0]]


@pytest.mark.django_db
@override_settings(AI_FEATURES_ENABLED=False, GEMINI_API_KEY="must-not-be-used")
def test_chat_respects_global_ai_feature_switch():
    session = ChatSession.objects.create(guest_token="guest-token-feature-disabled")

    with patch.object(GeminiProvider, "generate_chat") as generate_chat:
        events = list(AIChatService().handle_turn(session, "Tìm laptop học tập"))

    generate_chat.assert_not_called()
    assert "chưa tìm thấy sản phẩm khớp" in events[-2].text
    assert events[-1].type == "done"
    assert AIRequestLog.objects.get(feature=AIRequestLog.Feature.CHAT_TURN).status == (
        AIRequestLog.Status.FALLBACK
    )


@pytest.mark.django_db
def test_chat_stops_tool_execution_at_iteration_limit():
    provider = Mock(spec=BaseAIProvider)
    provider.name = "gemini"

    def generate_chat(*, tools, **kwargs):
        if not tools:
            return iter(
                [
                    ChatChunk(
                        delta_text="Đây là kết quả với dữ liệu hiện có.",
                        input_tokens=2,
                        output_tokens=1,
                    )
                ]
            )
        return iter(
            [
                ChatChunk(
                    tool_calls=[
                        ToolCall(
                            id=f"call-{provider.generate_chat.call_count}",
                            name="get_policy",
                            arguments={"topic": "giao hàng"},
                        )
                    ],
                    input_tokens=2,
                    output_tokens=1,
                )
            ]
        )

    provider.generate_chat.side_effect = generate_chat
    executor = Mock(return_value={"documents": []})
    session = ChatSession.objects.create(guest_token="guest-token-tool-limit")

    events = list(
        AIChatService(provider=provider, tool_executor=executor).handle_turn(
            session,
            "Cho tôi biết chính sách",
        )
    )

    assert executor.call_count == AIChatService.MAX_TOOL_ITERATIONS
    assert provider.generate_chat.call_count == AIChatService.MAX_TOOL_ITERATIONS + 1
    assert events[-1].message["content"] == "Đây là kết quả với dữ liệu hiện có."
    request_log = AIRequestLog.objects.get(feature=AIRequestLog.Feature.CHAT_TURN)
    assert request_log.input_tokens == (AIChatService.MAX_TOOL_ITERATIONS + 1) * 2
    assert request_log.output_tokens == AIChatService.MAX_TOOL_ITERATIONS + 1


@pytest.mark.django_db
def test_chat_closes_session_before_turn_31_without_calling_provider():
    provider = fake_provider([ChatChunk(delta_text="Không được gọi")])
    session = ChatSession.objects.create(
        guest_token="guest-token-turn-limit",
        turn_count=AIChatService.MAX_TURNS_PER_SESSION,
    )

    events = list(AIChatService(provider=provider).handle_turn(session, "Lượt tiếp theo"))

    session.refresh_from_db()
    assert session.status == ChatSession.Status.CLOSED
    assert events == [
        ChatEvent(
            type="error",
            text="Phiên chat đã đạt giới hạn 30 lượt. Vui lòng mở phiên mới.",
            code="turn_limit_reached",
        )
    ]
    provider.generate_chat.assert_not_called()


@pytest.mark.django_db
def test_chat_summarizes_messages_outside_context_window():
    session = ChatSession.objects.create(
        guest_token="guest-token-summary",
        turn_count=AIChatService.MAX_HISTORY_TURNS,
    )
    for index in range(AIChatService.MAX_HISTORY_TURNS):
        ChatMessage.objects.create(
            session=session,
            role=ChatMessage.Role.USER,
            content=f"Nhu cầu {index}",
        )
        ChatMessage.objects.create(
            session=session,
            role=ChatMessage.Role.ASSISTANT,
            content=f"Tư vấn {index}",
        )
    provider = fake_provider([ChatChunk(delta_text="Tư vấn lượt mới")])
    ai_service = AIService(provider=provider)
    ai_service.generate_text = Mock(
        return_value=AIResult(
            text="Khách cần laptop học tập dưới 20 triệu.",
            ai_used=True,
            fallback_used=False,
            cached=False,
            model_name="gemini-test",
        )
    )

    list(
        AIChatService(provider=provider, ai_service=ai_service).handle_turn(
            session,
            "Ưu tiên pin tốt",
        )
    )

    session.refresh_from_db()
    assert session.history_summary == "Khách cần laptop học tập dưới 20 triệu."
    sent_messages = provider.generate_chat.call_args.kwargs["messages"]
    assert len(sent_messages) <= AIChatService.MAX_HISTORY_TURNS * 2
    ai_service.generate_text.assert_called_once()


@pytest.mark.django_db
def test_get_policy_only_returns_verified_policy_documents():
    PolicyDocument.objects.all().delete()
    expected = PolicyDocument.objects.create(
        category=PolicyDocument.Category.RETURN,
        title="Đổi trả đã xác minh",
        content="Khách có thể gửi yêu cầu trong 7 ngày sau khi đơn hoàn thành.",
    )

    result = _get_policy("chính sách đổi trả")

    assert result["documents"] == [
        {
            "id": str(expected.pk),
            "category": PolicyDocument.Category.RETURN,
            "title": expected.title,
            "content": expected.content,
        }
    ]


@pytest.mark.django_db
def test_chat_throttle_isolated_by_session():
    client = APIClient()
    first_token = "first-guest-token-for-throttle"
    second_token = "second-guest-token-for-throttle"
    session = ChatSession.objects.create(guest_token=first_token)
    rest_framework = {
        **settings.REST_FRAMEWORK,
        "DEFAULT_THROTTLE_RATES": {
            **settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"],
            "ai_chat_session": "1/minute",
        },
    }

    with (
        override_settings(REST_FRAMEWORK=rest_framework),
        patch.object(AIChatService, "handle_turn", return_value=iter([])),
    ):
        first = client.post(
            "/api/v1/chat/turn",
            {"session_id": str(session.pk), "guest_token": first_token, "message": "Một"},
            format="json",
        )
        list(first.streaming_content)
        limited = client.post(
            "/api/v1/chat/turn",
            {"session_id": str(session.pk), "guest_token": first_token, "message": "Hai"},
            format="json",
        )
        other = client.post(
            "/api/v1/chat/turn",
            {"guest_token": second_token, "message": "Phiên khác"},
            format="json",
        )

    assert first.status_code == 200
    assert limited.status_code == 429
    assert other.status_code == 200


@pytest.mark.django_db
def test_chat_endpoint_streams_session_and_done_events():
    client = APIClient()
    assistant_message = {
        "id": str(uuid4()),
        "session_id": str(uuid4()),
        "role": "assistant",
        "content": "Xin chào",
        "attachments": [],
        "created_at": "2026-08-14T00:00:00+00:00",
    }
    with patch.object(
        AIChatService,
        "handle_turn",
        return_value=iter([ChatEvent(type="done", message=assistant_message)]),
    ):
        response = client.post(
            "/api/v1/chat/turn",
            {"guest_token": "guest-token-for-sse-test", "message": "Xin chào"},
            format="json",
            HTTP_ACCEPT="text/event-stream",
        )
        body = b"".join(response.streaming_content).decode()

    assert response.status_code == 200
    assert response["Content-Type"].startswith("text/event-stream")
    assert response["X-Accel-Buffering"] == "no"
    events = [json.loads(block.removeprefix("data: ")) for block in body.strip().split("\n\n")]
    assert events[0]["type"] == "session"
    assert events[-1] == {"type": "done", "message": assistant_message}


@pytest.mark.django_db
def test_authenticated_customer_can_claim_matching_guest_session():
    user = User.objects.create_user(email="chat-claim@example.com", password="StrongPass!234")
    token = "matching-guest-token-for-claim"
    session = ChatSession.objects.create(guest_token=token)
    client = APIClient()
    client.force_authenticate(user)

    with patch.object(AIChatService, "handle_turn", return_value=iter([])):
        response = client.post(
            "/api/v1/chat/turn",
            {"session_id": str(session.pk), "guest_token": token, "message": "Tiếp tục"},
            format="json",
        )
        list(response.streaming_content)

    session.refresh_from_db()
    assert response.status_code == 200
    assert session.user == user


@pytest.mark.django_db
def test_guest_history_requires_matching_token_and_hides_tool_messages():
    token = "matching-guest-token-for-history"
    session = ChatSession.objects.create(guest_token=token)
    ChatMessage.objects.create(session=session, role=ChatMessage.Role.USER, content="Tìm laptop")
    ChatMessage.objects.create(
        session=session,
        role=ChatMessage.Role.TOOL,
        content='{"products": []}',
    )
    ChatMessage.objects.create(
        session=session,
        role=ChatMessage.Role.ASSISTANT,
        content="Bạn có ngân sách bao nhiêu?",
    )
    client = APIClient()

    denied = client.get(
        f"/api/v1/chat/sessions/{session.pk}/messages",
        {"guest_token": "different-guest-token-history"},
    )
    allowed = client.get(
        f"/api/v1/chat/sessions/{session.pk}/messages",
        {"guest_token": token},
    )

    assert denied.status_code == 404
    assert allowed.status_code == 200
    assert [message["role"] for message in allowed.json()["data"]] == ["user", "assistant"]
