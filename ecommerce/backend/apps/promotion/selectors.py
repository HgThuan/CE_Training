from django.db.models import F, Prefetch, Q
from django.utils import timezone

from apps.account.models import Shop
from apps.product.models import Product
from apps.promotion.models import FlashSale, FlashSaleItem, Voucher


def platform_vouchers():
    return Voucher.objects.filter(scope=Voucher.Scope.PLATFORM).select_related(
        "applicable_category"
    )


def shop_vouchers(shop):
    return Voucher.objects.filter(
        scope=Voucher.Scope.SHOP,
        shop=shop,
    ).select_related("shop", "applicable_category")


def active_flash_sales():
    now = timezone.now()
    item_queryset = (
        FlashSaleItem.objects.select_related(
            "variant__inventory_balance",
            "variant__product__shop",
            "variant__shop",
        )
        .prefetch_related("variant__product__media")
        .filter(
            sold_count__lt=F("quota"),
            variant__is_active=True,
            variant__is_deleted=False,
            variant__product__status=Product.Status.APPROVED,
            variant__product__is_deleted=False,
            variant__shop__status=Shop.Status.APPROVED,
            variant__shop__is_deleted=False,
        )
        .filter(
            Q(variant__inventory_balance__available_stock__gt=0)
            | Q(
                variant__inventory_balance__isnull=True,
                variant__stock_quantity__gt=0,
            )
        )
    )
    return (
        FlashSale.objects.filter(
            is_active=True,
            start_time__lte=now,
            end_time__gte=now,
        )
        .prefetch_related(Prefetch("items", queryset=item_queryset))
        .order_by("end_time", "id")
    )
