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


class Wishlist(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="wishlist",
    )

    class Meta:
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"Wishlist {self.user_id}"


class WishlistItem(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    wishlist = models.ForeignKey(
        Wishlist,
        on_delete=models.CASCADE,
        related_name="items",
    )
    product = models.ForeignKey(
        "product.Product",
        on_delete=models.CASCADE,
        related_name="wishlist_items",
    )
    price_when_added = models.DecimalField(
        max_digits=18,
        decimal_places=0,
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ("-created_at", "-id")
        constraints = [
            models.UniqueConstraint(
                fields=("wishlist", "product"),
                name="eng_wishlist_product_uniq",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(price_when_added__isnull=True) | models.Q(price_when_added__gte=0)
                ),
                name="eng_wishlist_price_nonnegative",
            ),
        ]
        indexes = [
            models.Index(
                fields=("wishlist", "-created_at"),
                name="eng_wishlist_recent_idx",
            ),
            models.Index(
                fields=("product",),
                name="eng_wishlist_product_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.wishlist_id}: {self.product_id}"


class ShopFollower(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    shop = models.ForeignKey(
        "account.Shop",
        on_delete=models.CASCADE,
        related_name="followers",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="followed_shops",
    )

    class Meta:
        ordering = ("-created_at", "-id")
        constraints = [
            models.UniqueConstraint(
                fields=("shop", "user"),
                name="eng_shop_follower_uniq",
            )
        ]
        indexes = [
            models.Index(
                fields=("shop", "-created_at"),
                name="eng_shop_followers_idx",
            ),
            models.Index(
                fields=("user", "-created_at"),
                name="eng_user_follows_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.user_id} follows {self.shop_id}"
