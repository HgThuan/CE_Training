from rest_framework.permissions import BasePermission

from apps.account.models import Shop
from apps.promotion.models import Voucher


class IsVoucherShopOwner(BasePermission):
    message = "Bạn không có quyền truy cập voucher của shop khác"

    def has_object_permission(self, request, view, obj) -> bool:
        return bool(
            isinstance(obj, Voucher)
            and obj.scope == Voucher.Scope.SHOP
            and obj.shop_id
            and Shop.objects.filter(pk=obj.shop_id, owner=request.user).exists()
        )
