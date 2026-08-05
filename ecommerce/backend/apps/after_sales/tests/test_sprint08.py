from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.account.models import User
from apps.account.tests.factories import ShopFactory, UserFactory
from apps.after_sales.models import Dispute, ReturnRequest
from apps.after_sales.services import DisputeService, ReturnRequestService
from apps.common.models import AuditLog
from apps.order.models import Order, ShopOrder
from apps.order.services import CheckoutService
from apps.order.tests.test_services import checkout_fixture
from apps.payment.models import Payment, Refund

pytestmark = pytest.mark.django_db


def completed_paid_order():
    user, customer, address, shop, variant, balance, cart_item = checkout_fixture()
    order, _, _ = CheckoutService.checkout(
        customer=customer,
        cart_item_ids=[cart_item.pk],
        address_id=address.pk,
        coupons={},
        payment_method=Order.PaymentMethod.COD,
        idempotency_key=f"return-{user.pk}",
    )
    shop_order = order.shop_orders.get()
    shop_order.fulfillment_status = ShopOrder.FulfillmentStatus.COMPLETED
    shop_order.completed_at = timezone.now()
    shop_order.save(update_fields=("fulfillment_status", "completed_at", "updated_at"))
    Payment.objects.create(
        order=order,
        payment_code=f"PAY-RETURN-{user.pk}",
        method=Order.PaymentMethod.COD,
        provider=Order.PaymentMethod.COD,
        amount=order.grand_total,
        status=Payment.Status.PAID,
        idempotency_key=f"return-payment-{user.pk}",
        paid_at=timezone.now(),
    )
    order.payment_status = Order.PaymentStatus.PAID
    order.save(update_fields=("payment_status", "updated_at"))
    return user, shop, order, shop_order, shop_order.items.get()


def make_return_request():
    customer, shop, order, shop_order, item = completed_paid_order()
    request = ReturnRequestService.create(
        shop_order=shop_order,
        customer=customer,
        reason_code="DAMAGED",
        reason_detail="Sản phẩm bị vỡ",
        items=[{"order_item_id": item.pk, "quantity": 1}],
        media=[{"media_type": "IMAGE", "file_url": "https://example.com/damage.jpg"}],
    )
    return customer, shop, order, shop_order, item, request


def test_customer_can_create_return_for_completed_order():
    customer, shop, order, shop_order, item, request = make_return_request()

    request_item = request.items.get()
    shop_order.refresh_from_db()
    assert request.status == ReturnRequest.Status.REQUESTED
    assert request_item.quantity == 1
    assert request_item.requested_refund_amount == item.line_total / item.quantity
    assert shop_order.fulfillment_status == ShopOrder.FulfillmentStatus.RETURN_REQUESTED


def test_seller_approval_creates_cod_settlement_and_refund():
    customer, customer_profile, address, shop, variant, balance, cart_item = checkout_fixture()
    order, _, _ = CheckoutService.checkout(
        customer=customer_profile,
        cart_item_ids=[cart_item.pk],
        address_id=address.pk,
        coupons={},
        payment_method=Order.PaymentMethod.COD,
        idempotency_key=f"cod-return-{customer.pk}",
    )
    shop_order = order.shop_orders.get()
    shop_order.fulfillment_status = ShopOrder.FulfillmentStatus.COMPLETED
    shop_order.completed_at = timezone.now()
    shop_order.save(update_fields=("fulfillment_status", "completed_at", "updated_at"))
    item = shop_order.items.get()
    request = ReturnRequestService.create(
        shop_order=shop_order,
        customer=customer,
        reason_code="DAMAGED",
        reason_detail="Hàng lỗi",
        items=[{"order_item_id": item.pk, "quantity": 1}],
    )

    ReturnRequestService.seller_decide(
        request, seller=shop.owner, action="APPROVE", response="Đồng ý hoàn"
    )

    request.refresh_from_db()
    assert request.status == ReturnRequest.Status.REFUNDED
    assert Payment.objects.filter(order=order, status=Payment.Status.PAID).exists()
    assert Refund.objects.filter(return_request=request, status=Refund.Status.SUCCEEDED).exists()


def test_return_reject_escalate_and_admin_full_refund_is_audited():
    customer, shop, order, shop_order, item, request = make_return_request()
    ReturnRequestService.seller_decide(
        request, seller=shop.owner, action="REJECT", response="Không đủ chứng cứ"
    )
    dispute = ReturnRequestService.escalate(request, customer=customer)
    admin = UserFactory(role=User.Role.ADMIN, is_staff=True)

    resolved = DisputeService.resolve(
        dispute,
        admin=admin,
        decision=Dispute.Decision.REFUND_FULL,
        note="Chứng cứ khách hàng hợp lệ",
        request_id="test-request-id",
    )

    request.refresh_from_db()
    assert resolved.status == Dispute.Status.RESOLVED
    assert request.status == ReturnRequest.Status.REFUNDED
    assert Refund.objects.get(return_request=request).amount == item.line_total / item.quantity
    assert AuditLog.objects.filter(action="dispute.resolve", target_id=str(dispute.pk)).exists()


def test_admin_partial_refund_must_be_less_than_requested_total():
    customer, shop, order, shop_order, item, request = make_return_request()
    ReturnRequestService.seller_decide(
        request, seller=shop.owner, action="REJECT", response="Từ chối"
    )
    dispute = ReturnRequestService.escalate(request, customer=customer)
    admin = UserFactory(role=User.Role.ADMIN, is_staff=True)

    with pytest.raises(Exception, match="nhỏ hơn tổng yêu cầu"):
        DisputeService.resolve(
            dispute,
            admin=admin,
            decision=Dispute.Decision.REFUND_PARTIAL,
            refund_amount=item.line_total,
            note="Sai số tiền",
        )


def test_seller_customer_list_is_scoped_and_aggregated():
    customer, shop, order, shop_order, item = completed_paid_order()
    other_shop = ShopFactory()
    client = APIClient()
    client.force_authenticate(shop.owner)

    response = client.get("/api/v1/seller/customers")

    assert response.status_code == 200
    assert response.data["meta"]["total_items"] == 1
    assert response.data["data"][0]["email"] == customer.email
    assert Decimal(response.data["data"][0]["total_spent"]) == shop_order.total_amount
    assert other_shop.owner.email != response.data["data"][0]["email"]
