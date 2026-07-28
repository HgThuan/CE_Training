from rest_framework.permissions import BasePermission

from apps.account.models import User
from apps.product.models import ProductVariant

from .models import InventoryBalance, StockEntry, StockOutEntry


class IsSeller(BasePermission):
    message = "Chỉ Seller mới có quyền quản lý tồn kho"

    def has_permission(self, request, view) -> bool:
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == User.Role.SELLER
        )


class IsInventoryOwner(BasePermission):
    message = "Bạn không có quyền truy cập dữ liệu kho của gian hàng này"

    def has_permission(self, request, view) -> bool:
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj) -> bool:
        if isinstance(obj, InventoryBalance):
            owner_id = obj.variant.shop.owner_id
        elif isinstance(obj, ProductVariant):
            owner_id = obj.shop.owner_id
        elif isinstance(obj, (StockEntry, StockOutEntry)):
            owner_id = obj.shop.owner_id
        else:
            return False
        return owner_id == request.user.pk

