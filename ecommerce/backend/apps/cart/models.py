import uuid

from django.db import models
from django.db.models import Q

from apps.common.models import TimeStampedModel


class Cart(TimeStampedModel):
    """Persistent cart for an authenticated customer.

    Guest carts intentionally live in browser localStorage and are sent to the
    merge endpoint after login. This keeps anonymous session state out of the
    database for Sprint 06.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        "account.CustomerProfile",
        on_delete=models.CASCADE,
        related_name="cart",
    )

    class Meta:
        ordering = ("-updated_at",)

    def __str__(self) -> str:
        return f"Cart(CustomerProfile: {self.user_id})"


class CartItem(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    variant = models.ForeignKey(
        "product.ProductVariant",
        on_delete=models.PROTECT,
        related_name="cart_items",
    )
    quantity = models.PositiveIntegerField()
    is_selected = models.BooleanField(default=True)
    unit_price_snapshot = models.DecimalField(max_digits=18, decimal_places=0)

    class Meta:
        ordering = ("created_at", "id")
        constraints = [
            models.UniqueConstraint(
                fields=("cart", "variant"),
                name="cart_item_cart_variant_uniq",
            ),
            models.CheckConstraint(
                condition=Q(quantity__gt=0),
                name="cart_item_quantity_positive",
            ),
            models.CheckConstraint(
                condition=Q(unit_price_snapshot__gte=0),
                name="cart_item_snapshot_nonnegative",
            ),
        ]
        indexes = [
            models.Index(fields=("cart", "is_selected"), name="cart_item_selected_idx"),
        ]

    def __str__(self) -> str:
        return f"CartItem({self.variant_id}, quantity={self.quantity})"
