import uuid

from django.db import models
from django.db.models import Q

from apps.common.models import TimeStampedModel


class Payment(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Chờ thanh toán"
        PAID = "PAID", "Đã thanh toán"
        FAILED = "FAILED", "Thất bại"
        EXPIRED = "EXPIRED", "Hết hạn"
        CANCELLED = "CANCELLED", "Đã hủy"
        REFUND_PENDING = "REFUND_PENDING", "Chờ hoàn tiền"
        REFUNDED = "REFUNDED", "Đã hoàn tiền"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey("order.Order", on_delete=models.PROTECT, related_name="payments")
    payment_code = models.CharField(max_length=50, unique=True, db_index=True)
    method = models.CharField(max_length=20)
    provider = models.CharField(max_length=30, null=True, blank=True)
    amount = models.DecimalField(max_digits=18, decimal_places=0)
    currency = models.CharField(max_length=3, default="VND")
    status = models.CharField(
        max_length=30, choices=Status.choices, default=Status.PENDING, db_index=True
    )
    idempotency_key = models.CharField(max_length=120, unique=True)
    provider_reference = models.CharField(max_length=120, null=True, blank=True, unique=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    failure_code = models.CharField(max_length=100, null=True, blank=True)
    failure_message = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "payments"
        ordering = ("-created_at",)
        constraints = [
            models.CheckConstraint(condition=Q(amount__gte=0), name="payment_amount_nonnegative")
        ]


class PaymentTransaction(models.Model):
    class ProcessingStatus(models.TextChoices):
        RECEIVED = "RECEIVED", "Đã nhận"
        PROCESSED = "PROCESSED", "Đã xử lý"
        IGNORED_DUPLICATE = "IGNORED_DUPLICATE", "Bỏ qua do trùng"
        FAILED = "FAILED", "Thất bại"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment = models.ForeignKey(Payment, on_delete=models.PROTECT, related_name="transactions")
    event_type = models.CharField(max_length=30)
    provider_event_id = models.CharField(max_length=150, null=True, blank=True, unique=True)
    provider_transaction_id = models.CharField(max_length=150, null=True, blank=True)
    request_payload = models.JSONField(null=True, blank=True)
    response_payload = models.JSONField(null=True, blank=True)
    signature_valid = models.BooleanField(null=True)
    processing_status = models.CharField(
        max_length=30,
        choices=ProcessingStatus.choices,
        default=ProcessingStatus.RECEIVED,
    )
    error_code = models.CharField(max_length=100, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "payment_transactions"
        ordering = ("-created_at",)

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValueError("PaymentTransaction là append-only")
        return super().save(*args, **kwargs)


class Refund(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Chờ xử lý"
        PROCESSING = "PROCESSING", "Đang xử lý"
        SUCCEEDED = "SUCCEEDED", "Thành công"
        FAILED = "FAILED", "Thất bại"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment = models.ForeignKey(Payment, on_delete=models.PROTECT, related_name="refunds")
    # ReturnRequest is introduced in Sprint 08; keep the nullable reference without a premature FK.
    return_request_id = models.UUIDField(null=True, blank=True)
    shop_order = models.ForeignKey(
        "order.ShopOrder", on_delete=models.PROTECT, null=True, blank=True, related_name="refunds"
    )
    refund_code = models.CharField(max_length=50, unique=True, db_index=True)
    amount = models.DecimalField(max_digits=18, decimal_places=0)
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    provider_reference = models.CharField(max_length=150, null=True, blank=True)
    idempotency_key = models.CharField(max_length=120, unique=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "refunds"
        constraints = [
            models.CheckConstraint(condition=Q(amount__gt=0), name="refund_amount_positive")
        ]
