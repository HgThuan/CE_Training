from decimal import Decimal
from unittest.mock import Mock, patch

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.account.models import CustomerProfile, User
from apps.account.tests.factories import ShopFactory, UserFactory
from apps.ai.chat_service import AIChatService
from apps.ai.models import ChatFeedback, ChatHandoff, ChatMessage, ChatSession
from apps.ai.providers import BaseAIProvider
from apps.ai.tools import _get_order_support
from apps.order.models import Order, ShopOrder


def make_customer_order(*, email: str = "chat-order@example.com"):
    user = UserFactory(email=email, role=User.Role.CUSTOMER)
    customer = CustomerProfile.objects.create(user=user)
    order = Order.objects.create(
        order_code="ORD-20260820-ABCDEF1234",
        customer=customer,
        subtotal=Decimal("200000"),
        grand_total=Decimal("230000"),
        shipping_total=Decimal("30000"),
        payment_status=Order.PaymentStatus.PAID,
        payment_method=Order.PaymentMethod.COD,
        idempotency_key=f"chat-order-{user.pk}",
    )
    shop_order = ShopOrder.objects.create(
        order=order,
        shop=ShopFactory(),
        shop_order_code="SORD-20260820-ABCDEF1234",
        fulfillment_status=ShopOrder.FulfillmentStatus.SHIPPING,
        subtotal=Decimal("200000"),
        shipping_fee=Decimal("30000"),
        total_amount=Decimal("230000"),
        shipping_method_name="Giao hàng tiêu chuẩn",
    )
    return user, order, shop_order


@pytest.mark.django_db
def test_order_support_only_returns_authenticated_customers_own_orders():
    owner, order, _ = make_customer_order()
    stranger = UserFactory(role=User.Role.CUSTOMER)
    CustomerProfile.objects.create(user=stranger)

    anonymous_result = _get_order_support(user=None)
    stranger_result = _get_order_support(order_code=order.order_code, user=stranger)
    owner_result = _get_order_support(order_code=order.order_code, user=owner)

    assert anonymous_result["code"] == "authentication_required"
    assert stranger_result["orders"] == []
    assert owner_result["source"] == "oms"
    assert owner_result["orders"][0]["order_code"] == order.order_code
    assert owner_result["orders"][0]["shop_orders"][0]["estimated_delivery_at"] is None


@pytest.mark.django_db
def test_guest_order_question_is_routed_without_calling_external_ai():
    provider = Mock(spec=BaseAIProvider)
    session = ChatSession.objects.create(guest_token="guest-token-order-support-test")

    events = list(
        AIChatService(provider=provider).handle_turn(session, "Đơn hàng của tôi tới đâu?")
    )

    done = events[-1].message
    assert "cần đăng nhập" in done["content"]
    assert done["attachments"][0]["type"] == "quick_actions"
    assert done["attachments"][0]["actions"][0]["value"] == "/auth/login"
    provider.generate_chat.assert_not_called()


@pytest.mark.django_db
def test_human_handoff_keeps_sanitized_conversation_context():
    session = ChatSession.objects.create(guest_token="guest-token-human-handoff-test")
    service = AIChatService(provider=Mock(spec=BaseAIProvider))

    list(service.handle_turn(session, "Tôi cần hỗ trợ về đơn hàng"))
    events = list(service.handle_turn(session, "Tôi muốn gặp nhân viên hỗ trợ"))

    session.refresh_from_db()
    handoff = ChatHandoff.objects.get(session=session)
    assert session.status == ChatSession.Status.ESCALATED
    assert handoff.status == ChatHandoff.Status.OPEN
    assert any(item["role"] == ChatMessage.Role.USER for item in handoff.context_snapshot)
    assert events[-1].message["attachments"][0]["type"] == "handoff_card"


@pytest.mark.django_db
def test_feedback_endpoint_is_scoped_to_session_owner():
    owner = UserFactory(role=User.Role.CUSTOMER)
    stranger = UserFactory(role=User.Role.CUSTOMER)
    session = ChatSession.objects.create(user=owner)
    message = ChatMessage.objects.create(
        session=session,
        role=ChatMessage.Role.ASSISTANT,
        content="Câu trả lời đã xác minh.",
    )
    client = APIClient()
    client.force_authenticate(stranger)
    denied = client.post(
        f"/api/v1/chat/messages/{message.pk}/feedback",
        {"rating": 1, "resolved": False},
        format="json",
    )

    client.force_authenticate(owner)
    allowed = client.post(
        f"/api/v1/chat/messages/{message.pk}/feedback",
        {"rating": 5, "resolved": True},
        format="json",
    )

    assert denied.status_code == 404
    assert allowed.status_code == 200
    feedback = ChatFeedback.objects.get(message=message)
    assert feedback.submitted_by == owner
    assert feedback.rating == 5
    assert feedback.resolved is True


@pytest.mark.django_db
def test_chat_turn_stores_only_normalized_product_ids_in_session_context():
    client = APIClient()
    product_id = "1e41f46c-e4f5-43df-8227-0e8dfbd3e0e9"
    with patch.object(AIChatService, "handle_turn", return_value=iter([])):
        response = client.post(
            "/api/v1/chat/turn",
            {
                "guest_token": "guest-token-context-storage-test",
                "message": "Gợi ý cho tôi",
                "browsing_history": [product_id, product_id],
                "channel": "web",
            },
            format="json",
        )
        list(response.streaming_content)

    session = ChatSession.objects.get(guest_token="guest-token-context-storage-test")
    assert session.context == {"browsing_history": [product_id], "channel": "web"}
    assert session.experiment_variant in {"control", "guided_actions"}
    assert session.created_at <= timezone.now()
