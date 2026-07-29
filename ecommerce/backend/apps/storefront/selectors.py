from django.db.models import Q, QuerySet
from django.utils import timezone

from apps.catalog.selectors import CategorySelector
from apps.product.models import Product
from apps.product.selectors import ProductSelector

from .models import Banner


def get_active_banners(position: str | None = None) -> QuerySet[Banner]:
    now = timezone.now()
    queryset = Banner.objects.filter(
        is_active=True,
        is_deleted=False,
    ).filter(
        Q(starts_at__isnull=True) | Q(starts_at__lte=now),
        Q(ends_at__isnull=True) | Q(ends_at__gt=now),
    )
    if position:
        queryset = queryset.filter(position=position)
    return queryset.order_by("position", "sort_order", "created_at", "id")


def get_admin_banners() -> QuerySet[Banner]:
    return Banner.objects.filter(is_deleted=False).order_by(
        "position",
        "sort_order",
        "created_at",
        "id",
    )


def get_banner_for_admin(banner_id) -> Banner | None:
    return Banner.objects.filter(pk=banner_id, is_deleted=False).first()


def get_home_products() -> tuple[QuerySet[Product], QuerySet[Product]]:
    public_products = ProductSelector.public_queryset()
    return (
        public_products.order_by("-created_at", "id")[:8],
        public_products.order_by("-sold_count", "-rating_average", "-created_at", "id")[:8],
    )


def get_home_categories():
    return CategorySelector.public_tree()
