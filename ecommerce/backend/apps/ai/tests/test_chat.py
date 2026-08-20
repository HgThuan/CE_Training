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
from apps.ai.providers import BaseAIProvider, ChatChunk, ToolCall
from apps.ai.providers.gemini import GeminiProvider
from apps.ai.services import AIResult, AIService
from apps.ai.tools import _get_policy


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
    executor = Mock(return_value={"products": [product], "result_count": 1})
    session = ChatSession.objects.create(guest_token="guest-token-for-chat-tests")

    events = list(
        AIChatService(provider=provider, tool_executor=executor).handle_turn(
            session,
            "Tìm laptop học tập",
        )
    )

    done = events[-1].to_dict()["message"]
    assert done["content"] == "Mình tìm thấy một lựa chọn phù hợp."
    assert done["attachments"] == [
        {"type": "product_card", "product_id": product["id"], "product": product}
    ]
    assert ChatMessage.objects.filter(session=session, role=ChatMessage.Role.TOOL).count() == 1
    assert AIRequestLog.objects.get(feature=AIRequestLog.Feature.CHAT_TURN).metadata[
        "tool_names"
    ] == ["search_products"]


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
    assert "tạm gián đoạn" in events[-2].text
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
