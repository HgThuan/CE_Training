import uuid

from django.conf import settings
from django.db import models

from apps.common.models import TimeStampedModel


class ProductQuestion(TimeStampedModel):
    class Status(models.TextChoices):
        VISIBLE = "visible", "Hiển thị"
        HIDDEN = "hidden", "Đã ẩn"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(
        "product.Product",
        on_delete=models.CASCADE,
        related_name="questions",
    )
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="product_questions",
    )
    content = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.VISIBLE,
        db_index=True,
    )

    class Meta:
        ordering = ("-created_at", "-id")
        indexes = [
            models.Index(
                fields=("product", "status", "-created_at"),
                name="eng_question_public_idx",
            ),
            models.Index(
                fields=("customer", "-created_at"),
                name="eng_question_customer_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.product_id}: {self.content[:60]}"


class ProductAnswer(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    question = models.OneToOneField(
        ProductQuestion,
        on_delete=models.CASCADE,
        related_name="answer",
    )
    seller_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="product_answers",
    )
    content = models.TextField()

    class Meta:
        ordering = ("created_at", "id")

    def __str__(self) -> str:
        return f"Answer for {self.question_id}"
