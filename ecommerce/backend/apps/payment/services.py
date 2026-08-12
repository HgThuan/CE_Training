import logging
from uuid import uuid4

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.common.exceptions import BusinessError
from apps.order.models import Order

from .models import Payment, PaymentTransaction, Refund
from .providers import CODProvider, VNPayProvider

payment_logger = logging.getLogger("payment")


class PaymentService:
    PROVIDERS = {Order.PaymentMethod.COD: CODProvider, Order.PaymentMethod.VNPAY: VNPayProvider}

    @classmethod
    def provider_for(cls, method: str):
        provider = cls.PROVIDERS.get(method.upper())
        if provider is None:
            raise BusinessError("Cổng thanh toán không được hỗ trợ", http_status=404)
        return provider()

    @classmethod
    def create_payment_intent(cls, order, *, renew_reference: bool = False) -> tuple[Payment, str]:
        existing = (
            order.payments.filter(status=Payment.Status.PENDING).order_by("-created_at").first()
        )
        if existing is not None:
            if renew_reference or not existing.payment_code.isalnum():
                existing.payment_code = f"PAY{uuid4().hex.upper()}"
                existing.save(update_fields=("payment_code", "updated_at"))
            url = cls.provider_for(existing.method).create_payment_url(order, existing.payment_code)
            return existing, url
        payment_code = f"PAY{uuid4().hex.upper()}"
        payment = Payment.objects.create(
            order=order,
            payment_code=payment_code,
            method=order.payment_method,
            provider=order.payment_method,
            amount=order.grand_total,
            currency=order.currency,
            idempotency_key=f"payment:{order.id}:{payment_code}",
        )
        provider = cls.provider_for(order.payment_method)
        url = provider.create_payment_url(order, payment.payment_code)
        PaymentTransaction.objects.create(
            payment=payment,
            event_type="redirect",
            request_payload={"order_id": str(order.pk), "amount": str(order.grand_total)},
            response_payload={"payment_url": url},
            processing_status=PaymentTransaction.ProcessingStatus.PROCESSED,
        )
        return payment, url

    @classmethod
    def handle_callback(cls, provider_name: str, raw_payload: dict) -> Payment:
        payment_logger.info("Payment callback received", extra={"provider": provider_name})
        try:
            result = cls.provider_for(provider_name).verify_callback(raw_payload)
        except BusinessError:
            payment_logger.warning("Payment callback signature or payload rejected")
            transaction_ref = str(raw_payload.get("vnp_TxnRef", ""))
            payment = Payment.objects.filter(payment_code=transaction_ref).first()
            if payment is not None:
                PaymentTransaction.objects.create(
                    payment=payment,
                    event_type="callback",
                    request_payload=raw_payload,
                    signature_valid=False,
                    processing_status=PaymentTransaction.ProcessingStatus.FAILED,
                    error_code="INVALID_SIGNATURE_OR_PAYLOAD",
                )
            raise
        with transaction.atomic():
            payment = (
                Payment.objects.select_for_update()
                .select_related("order")
                .filter(payment_code=result.transaction_ref)
                .first()
            )
            if payment is None:
                raise BusinessError("Không tìm thấy giao dịch thanh toán", http_status=404)
            order = Order.objects.select_for_update().get(pk=payment.order_id)
            duplicate = PaymentTransaction.objects.filter(
                provider_event_id=result.provider_event_id
            ).exists() or payment.status in {Payment.Status.PAID, Payment.Status.FAILED}
            if duplicate:
                PaymentTransaction.objects.create(
                    payment=payment,
                    event_type="callback",
                    request_payload=raw_payload,
                    signature_valid=True,
                    processing_status=PaymentTransaction.ProcessingStatus.IGNORED_DUPLICATE,
                )
                return payment
            if result.amount != payment.amount or result.currency != payment.currency:
                PaymentTransaction.objects.create(
                    payment=payment,
                    event_type="callback",
                    provider_event_id=result.provider_event_id,
                    provider_transaction_id=result.provider_transaction_id,
                    request_payload=raw_payload,
                    signature_valid=True,
                    processing_status=PaymentTransaction.ProcessingStatus.FAILED,
                    error_code="AMOUNT_OR_CURRENCY_MISMATCH",
                )
                payment_logger.error("Payment callback amount mismatch")
                raise BusinessError("Số tiền thanh toán không khớp", http_status=409)
            target = Payment.Status.PAID if result.successful else Payment.Status.FAILED
            PaymentTransaction.objects.create(
                payment=payment,
                event_type="callback",
                provider_event_id=result.provider_event_id,
                provider_transaction_id=result.provider_transaction_id,
                request_payload=raw_payload,
                signature_valid=True,
                processing_status=PaymentTransaction.ProcessingStatus.PROCESSED,
            )
            payment.status = target
            payment.provider_reference = result.provider_transaction_id
            fields = ["status", "provider_reference", "updated_at"]
            if result.successful:
                payment.paid_at = timezone.now()
                order.payment_status = Order.PaymentStatus.PAID
                fields.append("paid_at")
            else:
                payment.failed_at = timezone.now()
                payment.failure_code = result.response_code
                order.payment_status = Order.PaymentStatus.FAILED
                fields.extend(("failed_at", "failure_code"))
            payment.save(update_fields=fields)
            order.save(update_fields=("payment_status", "updated_at"))
            if not result.successful:
                from apps.order.models import ShopOrder
                from apps.order.services import OrderService

                for shop_order in order.shop_orders.filter(
                    fulfillment_status=ShopOrder.FulfillmentStatus.PENDING_CONFIRMATION
                ):
                    OrderService.cancel(
                        shop_order,
                        order.customer.user,
                        "PAYMENT_FAILED",
                        f"VNPay response code {result.response_code}",
                    )
            return payment

    @classmethod
    @transaction.atomic
    def refund(cls, shop_order, reason: str, *, process_provider=True) -> Refund:
        payment = (
            Payment.objects.select_for_update()
            .filter(order=shop_order.order, status=Payment.Status.PAID)
            .order_by("-paid_at")
            .first()
        )
        if payment is None:
            raise BusinessError(
                "Không tìm thấy payment đã thanh toán để hoàn tiền", http_status=409
            )
        key = f"cancel:{shop_order.pk}"
        refunded_or_pending = (
            Refund.objects.filter(payment=payment)
            .exclude(idempotency_key=key)
            .exclude(status=Refund.Status.FAILED)
            .aggregate(total=Sum("amount"))["total"]
            or 0
        )
        if refunded_or_pending + shop_order.total_amount > payment.amount:
            raise BusinessError("Tổng tiền hoàn vượt quá payment gốc", http_status=409)
        refund, created = Refund.objects.get_or_create(
            idempotency_key=key,
            defaults={
                "payment": payment,
                "shop_order": shop_order,
                "refund_code": f"RF-{uuid4().hex.upper()}",
                "amount": shop_order.total_amount,
                "reason": reason,
            },
        )
        if created:
            Order.objects.filter(pk=shop_order.order_id).update(
                payment_status=Order.PaymentStatus.REFUND_PENDING,
                updated_at=timezone.now(),
            )
        if process_provider and refund.status == Refund.Status.PENDING:
            cls.process_refund(refund)
        return refund

    @classmethod
    def process_refund(cls, refund) -> Refund:
        result = cls.provider_for(refund.payment.method).create_refund(refund.payment, refund)
        refund.status = Refund.Status.SUCCEEDED if result.successful else Refund.Status.FAILED
        refund.provider_reference = result.provider_reference
        refund.processed_at = timezone.now()
        refund.save(update_fields=("status", "provider_reference", "processed_at", "updated_at"))
        if result.successful:
            refunded = (
                Refund.objects.filter(
                    payment=refund.payment, status=Refund.Status.SUCCEEDED
                ).aggregate(total=Sum("amount"))["total"]
                or 0
            )
            if refunded >= refund.payment.amount:
                Order.objects.filter(pk=refund.payment.order_id).update(
                    payment_status=Order.PaymentStatus.REFUNDED,
                    updated_at=timezone.now(),
                )
        return refund
