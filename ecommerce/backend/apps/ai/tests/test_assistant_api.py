import json
import threading
from unittest.mock import patch

import pytest
from asgiref.sync import async_to_sync
from rest_framework.test import APIClient

from apps.account.models import User
from apps.account.tests.factories import UserFactory
from apps.ai.assistant.schemas import AssistantEvent
from apps.ai.models import ChatMessage, ChatSession

MESSAGE_URL = "/api/v1/ai/assistant/messages"
CONVERSATIONS_URL = "/api/v1/ai/assistant/conversations/"


def _sse_events(response):
    body = _stream_body(response).decode()
    return [
        json.loads(line.removeprefix("data: "))
        for line in body.splitlines()
        if line.startswith("data: ")
    ]


def _stream_body(response):
    if not response.is_async:
        return b"".join(response.streaming_content)

    async def collect():
        return b"".join([chunk async for chunk in response.streaming_content])

    return async_to_sync(collect)()


@pytest.mark.django_db
@pytest.mark.parametrize("role", [User.Role.CUSTOMER, User.Role.SELLER, User.Role.ADMIN])
def test_assistant_is_available_to_every_authenticated_role(role):
    user = UserFactory(role=role)
    client = APIClient()
    client.force_authenticate(user)
    with patch("apps.ai.views.ShoppingAssistant.handle_turn", return_value=iter(())):
        response = client.post(MESSAGE_URL, {"message": "Tìm laptop"}, format="json")
        _stream_body(response)

    assert response.status_code == 200
    assert ChatSession.objects.filter(user=user).exists()


@pytest.mark.django_db
def test_guest_assistant_uses_token_scoped_conversations():
    token = "guest-session-token-1234567890"
    with patch("apps.ai.views.ShoppingAssistant.handle_turn", return_value=iter(())):
        response = APIClient().post(
            MESSAGE_URL,
            {"message": "Tìm laptop", "guest_token": token},
            format="json",
        )
        events = _sse_events(response)

    session = ChatSession.objects.get(guest_token=token, user__isnull=True)
    assert response.status_code == 200
    assert events[0]["conversation_id"] == str(session.pk)
    assert APIClient().get(CONVERSATIONS_URL, {"guest_token": token}).status_code == 200
    assert APIClient().get(CONVERSATIONS_URL).status_code == 400


@pytest.mark.django_db
def test_stream_creates_owned_conversation_and_returns_done_event(settings):
    settings.AI_FEATURES_ENABLED = True
    customer = UserFactory(role=User.Role.CUSTOMER)
    client = APIClient()
    client.force_authenticate(customer)
    done_message = {
        "id": "11111111-1111-1111-1111-111111111111",
        "conversation_id": "22222222-2222-2222-2222-222222222222",
        "role": "assistant",
        "content": "Kết quả đã xác minh",
        "attachments": [],
        "feedback": None,
        "created_at": "2026-01-01T00:00:00+00:00",
    }
    events = iter(
        [
            AssistantEvent(type="stage", stage="understanding"),
            AssistantEvent(type="delta", text="Kết quả đã xác minh"),
            AssistantEvent(type="done", message=done_message),
        ]
    )
    with patch("apps.ai.views.ShoppingAssistant.handle_turn", return_value=events):
        response = client.post(MESSAGE_URL, {"message": "Tìm laptop"}, format="json")
        streamed = _sse_events(response)

    assert response.status_code == 200
    assert streamed[0]["type"] == "conversation"
    assert streamed[-1]["type"] == "done"
    conversation = ChatSession.objects.get(user=customer)
    assert streamed[0]["conversation_id"] == str(conversation.pk)


@pytest.mark.django_db
def test_assistant_stream_is_async_and_sends_heartbeats_while_work_is_blocked(settings):
    settings.AI_ASSISTANT_HEARTBEAT_SECONDS = 0.05
    customer = UserFactory(role=User.Role.CUSTOMER)
    client = APIClient()
    client.force_authenticate(customer)
    release = threading.Event()

    def slow_events():
        release.wait(timeout=1)
        yield AssistantEvent(type="stage", stage="understanding")

    with patch("apps.ai.views.ShoppingAssistant.handle_turn", return_value=slow_events()):
        response = client.post(MESSAGE_URL, {"message": "Tìm laptop"}, format="json")

        async def first_chunks():
            stream = response.streaming_content
            conversation = await anext(stream)
            heartbeat = await anext(stream)
            release.set()
            stage = heartbeat
            for _ in range(20):
                stage = await anext(stream)
                if not stage.startswith(b":"):
                    break
            await stream.aclose()
            return conversation, heartbeat, stage

        try:
            conversation, heartbeat, stage = async_to_sync(first_chunks)()
        finally:
            release.set()

    assert response.is_async is True
    assert b'"type": "conversation"' in conversation
    assert heartbeat == b": keep-alive\n\n"
    assert b'"stage": "understanding"' in stage


@pytest.mark.django_db
def test_assistant_stream_fails_fast_when_worker_capacity_is_exhausted():
    customer = UserFactory(role=User.Role.CUSTOMER)
    client = APIClient()
    client.force_authenticate(customer)
    slots = threading.BoundedSemaphore(value=1)
    slots.acquire()

    try:
        with (
            patch("apps.ai.views._ASSISTANT_STREAM_SLOTS", slots),
            patch("apps.ai.views.ShoppingAssistant.handle_turn") as handle_turn,
        ):
            response = client.post(MESSAGE_URL, {"message": "Tìm laptop"}, format="json")
            events = _sse_events(response)
    finally:
        slots.release()

    assert events[-1]["type"] == "error"
    assert events[-1]["code"] == "assistant_busy"
    handle_turn.assert_not_called()


@pytest.mark.django_db
def test_conversation_crud_and_feedback_are_owner_scoped():
    owner = UserFactory(role=User.Role.CUSTOMER)
    stranger = UserFactory(role=User.Role.CUSTOMER)
    session = ChatSession.objects.create(user=owner, title="Laptop")
    message = ChatMessage.objects.create(
        session=session,
        role=ChatMessage.Role.ASSISTANT,
        content="Một câu trả lời",
    )
    owner_client = APIClient()
    owner_client.force_authenticate(owner)
    stranger_client = APIClient()
    stranger_client.force_authenticate(stranger)

    list_response = owner_client.get(CONVERSATIONS_URL)
    detail_url = f"{CONVERSATIONS_URL}{session.pk}/"
    detail_response = owner_client.get(detail_url)
    feedback_response = owner_client.post(
        f"/api/v1/ai/assistant/messages/{message.pk}/feedback",
        {"rating": 5, "resolved": True},
        format="json",
    )

    assert list_response.status_code == 200
    assert list_response.json()["data"][0]["id"] == str(session.pk)
    assert detail_response.json()["data"]["messages"][0]["content"] == "Một câu trả lời"
    assert feedback_response.status_code == 200
    assert stranger_client.get(detail_url).status_code == 404
    assert (
        stranger_client.post(
            f"/api/v1/ai/assistant/messages/{message.pk}/feedback",
            {"rating": 1},
            format="json",
        ).status_code
        == 404
    )
    assert owner_client.delete(detail_url).status_code == 200
    assert not ChatSession.objects.filter(pk=session.pk).exists()
