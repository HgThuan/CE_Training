import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q

from apps.common.models import TimeStampedModel


class Review(TimeStampedModel):
    class Status(models.TextChoices):
        VISIBLE = "VISIBLE", "Hiển thị"
        HIDDEN = "HIDDEN", "Đã ẩn"
        PENDING_MODERATION = "PENDING_MODERATION", "Chờ kiểm duyệt"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_item = models.OneToOneField(
        "order.OrderItem", on_delete=models.PROTECT, related_name="review"
    )
    product = models.ForeignKey("product.Product", on_delete=models.PROTECT, related_name="reviews")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="reviews"
    )
    rating = models.PositiveSmallIntegerField(db_index=True)
    content = models.TextField(blank=True)
    is_verified_purchase = models.BooleanField(default=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.VISIBLE, db_index=True
    )
    editable_until = models.DateTimeField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "reviews"
        ordering = ("-created_at",)
        constraints = [
            models.CheckConstraint(
                condition=Q(rating__gte=1) & Q(rating__lte=5),
                name="review_rating_between_1_and_5",
            )
        ]
        indexes = [
            models.Index(
                fields=("product", "status", "-created_at"), name="review_product_feed_idx"
            )
        ]


class ReviewMedia(models.Model):
    class MediaType(models.TextChoices):
        IMAGE = "IMAGE", "Ảnh"
        VIDEO = "VIDEO", "Video"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name="media")
    media_type = models.CharField(max_length=20, choices=MediaType.choices)
    file_url = models.URLField(max_length=1000)
    sort_order = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "review_media"
        ordering = ("sort_order", "created_at")


class ReviewReply(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    review = models.OneToOneField(Review, on_delete=models.CASCADE, related_name="reply")
    seller_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="review_replies"
    )
    content = models.TextField()

    class Meta:
        db_table = "review_replies"


class ReviewReport(TimeStampedModel):
    class Status(models.TextChoices):
        OPEN = "OPEN", "Đang chờ"
        RESOLVED = "RESOLVED", "Đã xử lý"
        REJECTED = "REJECTED", "Từ chối báo cáo"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    review = models.ForeignKey(Review, on_delete=models.PROTECT, related_name="reports")
    reported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="review_reports"
    )
    reason_code = models.CharField(max_length=50)
    reason_detail = models.TextField(blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.OPEN, db_index=True
    )
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="resolved_review_reports",
    )
    resolution_note = models.TextField(blank=True)

    class Meta:
        db_table = "review_reports"
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=("review", "reported_by"),
                condition=Q(status="OPEN"),
                name="review_report_active_reporter_uniq",
            )
        ]
