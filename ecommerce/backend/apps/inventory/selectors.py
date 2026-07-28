from django.db.models import F, QuerySet

from apps.account.models import Shop, User
from apps.common.exceptions import BusinessError
from apps.product.models import ProductVariant

from .models import InventoryBalance, StockEntry, StockMovement, StockOutEntry


def get_shop_for_seller(user) -> Shop:
    if getattr(user, "role", None) != User.Role.SELLER:
        raise BusinessError("Chỉ Seller mới có quyền quản lý tồn kho", http_status=403)
    shop = Shop.objects.filter(owner=user, is_deleted=False).first()
    if shop is None:
        raise BusinessError("Không tìm thấy gian hàng của Seller", http_status=404)
    return shop


def get_inventory_for_shop(shop: Shop) -> QuerySet[InventoryBalance]:
    return (
        InventoryBalance.objects.select_related(
            "variant",
            "variant__product",
            "variant__shop",
        )
        .filter(
            variant__shop=shop,
            variant__product__shop=shop,
            variant__is_deleted=False,
            variant__product__is_deleted=False,
        )
        .order_by("variant__product__name", "variant__sku")
    )


def get_low_stock_variants(shop: Shop) -> QuerySet[InventoryBalance]:
    return get_inventory_for_shop(shop).filter(
        available_stock__lte=F("low_stock_threshold")
    )


def get_movement_history(
    variant: ProductVariant | None,
    shop: Shop,
) -> QuerySet[StockMovement]:
    queryset = StockMovement.objects.select_related(
        "variant",
        "variant__product",
        "created_by",
    ).filter(
        variant__shop=shop,
        variant__product__shop=shop,
        variant__is_deleted=False,
        variant__product__is_deleted=False,
    )
    if variant is not None:
        queryset = queryset.filter(variant=variant)
    return queryset.order_by("-created_at", "-pk")


def get_stock_entries_for_shop(shop: Shop) -> QuerySet[StockEntry]:
    return (
        StockEntry.objects.select_related("shop", "created_by", "confirmed_by")
        .prefetch_related("items__variant__product")
        .filter(shop=shop)
        .order_by("-created_at", "-pk")
    )


def get_stock_out_entries_for_shop(shop: Shop) -> QuerySet[StockOutEntry]:
    return (
        StockOutEntry.objects.select_related("shop", "created_by", "confirmed_by")
        .prefetch_related("items__variant__product")
        .filter(shop=shop)
        .order_by("-created_at", "-pk")
    )
