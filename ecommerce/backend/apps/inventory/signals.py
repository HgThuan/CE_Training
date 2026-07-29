from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.common.cache_utils import invalidate_product_cache_on_commit
from apps.product.models import ProductVariant

from .models import InventoryBalance
from .notifications import InventoryNotificationService


@receiver(
    (post_save, post_delete),
    sender=InventoryBalance,
    dispatch_uid="inventory.invalidate_balance_product_caches",
)
def invalidate_balance_product_caches(
    instance: InventoryBalance,
    **kwargs,
) -> None:
    variant = (
        ProductVariant.objects.select_related("product", "shop")
        .filter(pk=instance.variant_id)
        .only("product__slug", "shop__slug")
        .first()
    )
    if variant is not None:
        invalidate_product_cache_on_commit(
            slug=variant.product.slug,
            shop_slug=variant.shop.slug,
        )


def stock_reached_low_threshold(*, balance) -> None:
    """Thin event boundary; threshold calculation remains inside StockService."""
    InventoryNotificationService.notify_low_stock(balance=balance)


def stock_became_available(*, variant, available_stock: int) -> None:
    """Thin event boundary; transition detection remains inside StockService."""
    InventoryNotificationService.notify_back_in_stock(
        variant=variant,
        available_stock=available_stock,
    )
