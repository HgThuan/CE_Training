from datetime import datetime, timedelta
from decimal import Decimal
from urllib.parse import parse_qs, urlparse

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


@override_settings(
    VNPAY_TMN_CODE="DEMOV210",
    VNPAY_HASH_SECRET="test-secret",
    VNPAY_PAYMENT_URL="https://sandbox.vnpayment.vn/paymentv2/vpcpay.html",
    VNPAY_RETURN_URL="http://localhost:8080/payment/return",
)
def test_payment_url_uses_vnpay_21_required_fields_and_rotates_legacy_reference():
    order, payment = make_payment()

    updated_payment, payment_url = PaymentService.create_payment_intent(order)

    updated_payment.refresh_from_db()
    assert updated_payment.pk == payment.pk
    assert updated_payment.payment_code.isalnum()
    params = {key: values[0] for key, values in parse_qs(urlparse(payment_url).query).items()}
    assert params["vnp_TxnRef"] == updated_payment.payment_code
    assert params["vnp_OrderInfo"].replace(" ", "").isalnum()
    assert "-" not in params["vnp_OrderInfo"]
    assert params["vnp_IpAddr"] == "127.0.0.1"
    assert params["vnp_ReturnUrl"] == "http://localhost:8080/payment/return"
    created_at = datetime.strptime(params["vnp_CreateDate"], "%Y%m%d%H%M%S")
    expires_at = datetime.strptime(params["vnp_ExpireDate"], "%Y%m%d%H%M%S")
    assert expires_at - created_at == timedelta(minutes=15)
    supplied_hash = params.pop("vnp_SecureHash")
    assert supplied_hash == VNPayProvider()._signature(params)


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
    payload["order_id"] = str(order.pk)

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
