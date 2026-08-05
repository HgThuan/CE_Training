import json

import pytest
from rest_framework.test import APIClient

from apps.account.models import Notification, User
from apps.account.tests.factories import ShopFactory, UserFactory
from apps.chat.models import Conversation, Message
from apps.chat.services import ConversationService

pytestmark = pytest.mark.django_db


def authenticated_client(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


def test_customer_opens_conversation_and_both_participants_can_list_it():
    customer = UserFactory(role=User.Role.CUSTOMER)
    shop = ShopFactory()

    response = authenticated_client(customer).post(
        "/api/v1/conversations", {"shop_slug": shop.slug}, format="json"
    )

    assert response.status_code == 201
    conversation = Conversation.objects.get()
    assert set(conversation.participants.values_list("user_id", flat=True)) == {
        customer.pk,
        shop.owner_id,
    }
    seller_response = authenticated_client(shop.owner).get("/api/v1/seller/conversations")
    assert seller_response.status_code == 200
    assert seller_response.data["data"][0]["id"] == str(conversation.pk)


def test_message_is_persisted_idempotently_and_notifies_recipient():
    customer = UserFactory(role=User.Role.CUSTOMER)
    shop = ShopFactory()
    conversation, _ = ConversationService.open(customer=customer, shop=shop)
    payload = {
        "message_type": "TEXT",
        "content": "Shop tư vấn giúp mình",
        "client_message_id": "client-message-1",
    }
    client = authenticated_client(customer)

    first = client.post(f"/api/v1/conversations/{conversation.pk}/messages", payload, format="json")
    retry = client.post(f"/api/v1/conversations/{conversation.pk}/messages", payload, format="json")

    assert first.status_code == 201
    assert retry.status_code == 200
    assert first.data["data"]["id"] == retry.data["data"]["id"]
    assert Message.objects.count() == 1
    assert Notification.objects.filter(user=shop.owner, kind=Notification.Kind.CHAT).count() == 1


def test_message_broadcast_payload_is_channel_layer_serializable(monkeypatch):
    customer = UserFactory(role=User.Role.CUSTOMER)
    shop = ShopFactory()
    conversation, _ = ConversationService.open(customer=customer, shop=shop)
    message, _ = ConversationService.send_message(
        conversation=conversation,
        sender=customer,
        message_type=Message.Type.TEXT,
        content="Tin nhắn realtime",
        client_message_id="broadcast-message-1",
    )
    sent_events = []

    class RecordingChannelLayer:
        async def group_send(self, group, event):
            sent_events.append((group, event))

    monkeypatch.setattr("apps.chat.services.get_channel_layer", lambda: RecordingChannelLayer())

    ConversationService.broadcast(message.pk)

    group, event = sent_events[0]
    json.dumps(event)
    assert group == f"conversation_{conversation.pk}"
    assert event["message"]["conversation"] == str(conversation.pk)
    assert event["message"]["id"] == str(message.pk)


def test_outsider_cannot_read_or_send_to_conversation():
    customer = UserFactory(role=User.Role.CUSTOMER)
    outsider = UserFactory(role=User.Role.CUSTOMER)
    conversation, _ = ConversationService.open(customer=customer, shop=ShopFactory())
    client = authenticated_client(outsider)

    assert client.get(f"/api/v1/conversations/{conversation.pk}/messages").status_code == 404
    assert (
        client.post(
            f"/api/v1/conversations/{conversation.pk}/messages",
            {"message_type": "TEXT", "content": "x", "client_message_id": "x"},
            format="json",
        ).status_code
        == 404
    )


def test_read_cursor_updates_unread_count():
    customer = UserFactory(role=User.Role.CUSTOMER)
    shop = ShopFactory()
    conversation, _ = ConversationService.open(customer=customer, shop=shop)
    message, _ = ConversationService.send_message(
        conversation=conversation,
        sender=shop.owner,
        message_type=Message.Type.TEXT,
        content="Đã phản hồi",
        client_message_id="seller-1",
    )
    client = authenticated_client(customer)

    before = client.get("/api/v1/conversations")
    marked = client.post(
        f"/api/v1/conversations/{conversation.pk}/read",
        {"message_id": str(message.pk)},
        format="json",
    )
    after = client.get("/api/v1/conversations")

    assert before.data["data"][0]["unread_count"] == 1
    assert marked.status_code == 200
    assert after.data["data"][0]["unread_count"] == 0
