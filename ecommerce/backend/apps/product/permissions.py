from rest_framework.permissions import BasePermission

from apps.account.models import User

from .models import Product, ProductMedia, ProductVariant


class IsShopOwner(BasePermission):
    """Object permission for Product entities owned by the authenticated Seller."""

    message = "Bạn không có quyền truy cập dữ liệu của gian hàng này"

    def has_permission(self, request, view) -> bool:
        return bool(
            request.user and request.user.is_authenticated and request.user.role == User.Role.SELLER
        )

    def has_object_permission(self, request, view, obj) -> bool:
        if isinstance(obj, Product):
            owner_id = obj.shop.owner_id
        elif isinstance(obj, ProductMedia):
            owner_id = obj.product.shop.owner_id
        elif isinstance(obj, ProductVariant):
            owner_id = obj.product.shop.owner_id
        else:
            return False
        return owner_id == request.user.pk
