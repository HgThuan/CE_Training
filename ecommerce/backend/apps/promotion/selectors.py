from django.db.models import Prefetch
from django.utils import timezone

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
    item_queryset = FlashSaleItem.objects.select_related(
        "variant__product__shop",
    ).prefetch_related("variant__product__media")
    return (
        FlashSale.objects.filter(
            is_active=True,
            start_time__lte=now,
            end_time__gte=now,
        )
        .prefetch_related(Prefetch("items", queryset=item_queryset))
        .order_by("end_time", "id")
    )
