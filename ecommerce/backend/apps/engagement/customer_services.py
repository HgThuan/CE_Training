from dataclasses import dataclass

from django.db import transaction

from apps.account.models import Shop, User
from apps.common.exceptions import BusinessError

from .customer_selectors import follower_count, get_public_product
from .models import ShopFollower, Wishlist, WishlistItem
from .services import _validate_actor


@dataclass(frozen=True)
class WishlistToggleResult:
    product_id: object
    is_wishlisted: bool
    item: WishlistItem | None


@dataclass(frozen=True)
class ShopFollowToggleResult:
    shop_id: int
    is_following: bool
    follower_count: int


def _lock_customer(customer):
    locked_customer = User.objects.select_for_update().filter(pk=customer.pk).first()
    if locked_customer is None:
        raise BusinessError("Không tìm thấy Customer", http_status=404)
    _validate_actor(
        locked_customer,
        role=User.Role.CUSTOMER,
        message="Chỉ Customer đang hoạt động mới có thể thực hiện thao tác này",
    )
    return locked_customer


class WishlistService:
    @staticmethod
    @transaction.atomic
    def toggle(*, customer, product_id) -> WishlistToggleResult:
        _validate_actor(
            customer,
            role=User.Role.CUSTOMER,
            message="Chỉ Customer đang hoạt động mới có thể dùng wishlist",
        )
        product = get_public_product(product_id)
        if product is None:
            raise BusinessError("Không tìm thấy sản phẩm", http_status=404)

        locked_customer = _lock_customer(customer)
        wishlist, _ = Wishlist.objects.get_or_create(user=locked_customer)
        existing = (
            WishlistItem.objects.select_for_update()
            .filter(wishlist=wishlist, product=product)
            .first()
        )
        if existing is not None:
            existing.delete()
            return WishlistToggleResult(
                product_id=product.pk,
                is_wishlisted=False,
                item=None,
            )

        item = WishlistItem.objects.create(
            wishlist=wishlist,
            product=product,
            price_when_added=product.min_price,
        )
        return WishlistToggleResult(
            product_id=product.pk,
            is_wishlisted=True,
            item=item,
        )


class ShopFollowService:
    @staticmethod
    @transaction.atomic
    def toggle(*, customer, shop_id: int) -> ShopFollowToggleResult:
        _validate_actor(
            customer,
            role=User.Role.CUSTOMER,
            message="Chỉ Customer đang hoạt động mới có thể theo dõi gian hàng",
        )
        locked_customer = _lock_customer(customer)
        shop = (
            Shop.objects.select_for_update()
            .filter(
                pk=shop_id,
                status=Shop.Status.APPROVED,
                is_deleted=False,
                owner__is_active=True,
                owner__is_deleted=False,
            )
            .first()
        )
        if shop is None:
            raise BusinessError("Không tìm thấy gian hàng", http_status=404)

        existing = (
            ShopFollower.objects.select_for_update().filter(shop=shop, user=locked_customer).first()
        )
        if existing is not None:
            existing.delete()
            is_following = False
        else:
            ShopFollower.objects.create(shop=shop, user=locked_customer)
            is_following = True

        return ShopFollowToggleResult(
            shop_id=shop.pk,
            is_following=is_following,
            follower_count=follower_count(shop=shop),
        )
