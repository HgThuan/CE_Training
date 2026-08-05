import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.common.models import TimeStampedModel


class ReturnRequest(TimeStampedModel):
    class Status(models.TextChoices):
        REQUESTED = "REQUESTED", "Đã yêu cầu"
        SELLER_APPROVED = "SELLER_APPROVED", "Seller đồng ý"
        SELLER_REJECTED = "SELLER_REJECTED", "Seller từ chối"
        RETURNING = "RETURNING", "Đang trả hàng"
        RECEIVED = "RECEIVED", "Đã nhận hàng trả"
        REFUND_PENDING = "REFUND_PENDING", "Chờ hoàn tiền"
        REFUNDED = "REFUNDED", "Đã hoàn tiền"
        ESCALATED = "ESCALATED", "Đã khiếu nại"
        CLOSED = "CLOSED", "Đã đóng"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    shop_order = models.ForeignKey(
        "order.ShopOrder", on_delete=models.PROTECT, related_name="return_requests"
    )
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="return_requests"
    )
    status = models.CharField(
        max_length=30, choices=Status.choices, default=Status.REQUESTED, db_index=True
    )
    reason_code = models.CharField(max_length=50)
    reason_detail = models.TextField()
    seller_response = models.TextField(blank=True)
    requested_at = models.DateTimeField(default=timezone.now, db_index=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "return_requests"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("shop_order", "status"), name="return_shop_order_status_idx"),
            models.Index(
                fields=("customer", "-requested_at"), name="return_customer_requested_idx"
            ),
        ]


class ReturnRequestItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    return_request = models.ForeignKey(
        ReturnRequest, on_delete=models.CASCADE, related_name="items"
    )
    order_item = models.ForeignKey(
        "order.OrderItem", on_delete=models.PROTECT, related_name="return_request_items"
    )
    quantity = models.PositiveIntegerField()
    requested_refund_amount = models.DecimalField(max_digits=18, decimal_places=0)
    approved_refund_amount = models.DecimalField(
        max_digits=18, decimal_places=0, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "return_request_items"
        constraints = [
            models.UniqueConstraint(
                fields=("return_request", "order_item"), name="return_request_item_uniq"
            ),
            models.CheckConstraint(
                condition=Q(quantity__gt=0), name="return_item_quantity_positive"
            ),
            models.CheckConstraint(
                condition=Q(requested_refund_amount__gte=0),
                name="return_item_requested_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(approved_refund_amount__isnull=True) | Q(approved_refund_amount__gte=0),
                name="return_item_approved_nonnegative",
            ),
        ]


class ReturnRequestMedia(models.Model):
    class MediaType(models.TextChoices):
        IMAGE = "IMAGE", "Ảnh"
        VIDEO = "VIDEO", "Video"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    return_request = models.ForeignKey(
        ReturnRequest, on_delete=models.CASCADE, related_name="media"
    )
    file_url = models.URLField(max_length=1000)
    media_type = models.CharField(max_length=20, choices=MediaType.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "return_request_media"
        ordering = ("created_at",)


class Dispute(TimeStampedModel):
    class Status(models.TextChoices):
        OPEN = "OPEN", "Mới mở"
        REVIEWING = "REVIEWING", "Đang xem xét"
        RESOLVED = "RESOLVED", "Đã giải quyết"
        CLOSED = "CLOSED", "Đã đóng"

    class Decision(models.TextChoices):
        REFUND_FULL = "REFUND_FULL", "Hoàn toàn bộ"
        REFUND_PARTIAL = "REFUND_PARTIAL", "Hoàn một phần"
        REJECT = "REJECT", "Từ chối"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    return_request = models.OneToOneField(
        ReturnRequest, on_delete=models.PROTECT, related_name="dispute", null=True, blank=True
    )
    shop_order = models.ForeignKey(
        "order.ShopOrder", on_delete=models.PROTECT, related_name="disputes"
    )
    opened_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="opened_disputes"
    )
    assigned_admin = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_disputes",
    )
    status = models.CharField(
        max_length=30, choices=Status.choices, default=Status.OPEN, db_index=True
    )
    decision = models.CharField(max_length=30, choices=Decision.choices, null=True, blank=True)
    decision_note = models.TextField(blank=True)
    refund_amount = models.DecimalField(max_digits=18, decimal_places=0, null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "disputes"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("status", "-created_at"), name="dispute_status_created_idx")
        ]


class DisputeEvidence(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    dispute = models.ForeignKey(Dispute, on_delete=models.CASCADE, related_name="evidence")
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="dispute_evidence"
    )
    content = models.TextField(blank=True)
    file_url = models.URLField(max_length=1000, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "dispute_evidence"
        ordering = ("created_at",)
