from django.db.models import Prefetch, QuerySet, Subquery

from apps.account.models import Shop, User
from apps.product.models import Product, ProductMedia
from apps.product.selectors import ProductSelector

from .models import ShopFollower, WishlistItem


def get_public_product(product_id) -> Product | None:
    return ProductSelector.public_base().filter(pk=product_id).first()


def get_wishlist_items(*, customer) -> QuerySet[WishlistItem]:
    public_product_ids = ProductSelector.public_base().values("pk")
    list_images = ProductMedia.objects.filter(
        media_type=ProductMedia.MediaType.IMAGE,
    ).order_by(
        "-is_primary",
        "sort_order",
        "created_at",
        "id",
    )
    return (
        WishlistItem.objects.filter(
            wishlist__user=customer,
            product_id__in=Subquery(public_product_ids),
        )
        .select_related(
            "product",
            "product__shop",
            "product__category",
            "product__brand",
        )
        .prefetch_related(
            Prefetch(
                "product__media",
                queryset=list_images,
                to_attr="_public_list_images",
            )
        )
        .order_by("-created_at", "-id")
    )


def follower_count(*, shop: Shop) -> int:
    return ShopFollower.objects.filter(
        shop=shop,
        user__role=User.Role.CUSTOMER,
        user__is_active=True,
        user__is_deleted=False,
    ).count()
