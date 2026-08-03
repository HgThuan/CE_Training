from decimal import Decimal

import pytest
from django.test import override_settings
from django.utils import timezone

from apps.account.models import CustomerProfile, User
from apps.account.tests.factories import UserFactory
from apps.common.exceptions import BusinessError
from apps.order.models import Order
from apps.payment.models import Payment, PaymentTransaction
from apps.payment.providers.vnpay_provider import VNPayProvider
from apps.payment.services import PaymentService

pytestmark = pytest.mark.django_db


def make_payment():
    user = UserFactory(role=User.Role.CUSTOMER)
    customer = CustomerProfile.objects.get_or_create(user=user)[0]
    order = Order.objects.create(
        order_code="ORD-PAYMENT-1",
        customer=customer,
        subtotal=Decimal("100000"),
        grand_total=Decimal("100000"),
        payment_method=Order.PaymentMethod.VNPAY,
        idempotency_key="pay-checkout",
        placed_at=timezone.now(),
    )
    payment = Payment.objects.create(
        order=order,
        payment_code="PAY-REF-1",
        method=Order.PaymentMethod.VNPAY,
        provider="VNPAY",
        amount=order.grand_total,
        idempotency_key="pay-attempt-1",
    )
    return order, payment


@override_settings(VNPAY_HASH_SECRET="test-secret")
def test_callback_is_idempotent_and_updates_order_once():
    order, payment = make_payment()
    payload = {
        "vnp_TxnRef": payment.payment_code,
        "vnp_Amount": "10000000",
        "vnp_CurrCode": "VND",
        "vnp_ResponseCode": "00",
        "vnp_TransactionStatus": "00",
        "vnp_TransactionNo": "VNP-001",
    }
    payload["vnp_SecureHash"] = VNPayProvider()._signature(payload)

    PaymentService.handle_callback("VNPAY", payload)
    PaymentService.handle_callback("VNPAY", payload)

    order.refresh_from_db()
    assert order.payment_status == Order.PaymentStatus.PAID
    assert (
        PaymentTransaction.objects.filter(
            processing_status=PaymentTransaction.ProcessingStatus.PROCESSED
        ).count()
        == 1
    )
    assert (
        PaymentTransaction.objects.filter(
            processing_status=PaymentTransaction.ProcessingStatus.IGNORED_DUPLICATE
        ).count()
        == 1
    )


@override_settings(VNPAY_HASH_SECRET="test-secret")
def test_callback_rejects_invalid_signature_and_amount():
    order, payment = make_payment()
    with pytest.raises(BusinessError, match="Chữ ký"):
        PaymentService.handle_callback(
            "VNPAY", {"vnp_TxnRef": payment.payment_code, "vnp_SecureHash": "bad"}
        )
    payload = {
        "vnp_TxnRef": payment.payment_code,
        "vnp_Amount": "9000000",
        "vnp_CurrCode": "VND",
        "vnp_ResponseCode": "00",
        "vnp_TransactionNo": "VNP-002",
    }
    payload["vnp_SecureHash"] = VNPayProvider()._signature(payload)
    with pytest.raises(BusinessError, match="không khớp"):
        PaymentService.handle_callback("VNPAY", payload)
    order.refresh_from_db()
    assert order.payment_status == Order.PaymentStatus.PENDING
