from rest_framework.permissions import BasePermission

from .models import SellerDocument, SellerProfile, Shop, User


class IsAdmin(BasePermission):
    message = "Chỉ Admin mới có quyền thực hiện thao tác này"

    def has_permission(self, request, view) -> bool:
        return bool(
            request.user and request.user.is_authenticated and request.user.role == User.Role.ADMIN
        )


class IsSeller(BasePermission):
    message = "Chỉ Seller mới có quyền thực hiện thao tác này"

    def has_permission(self, request, view) -> bool:
        return bool(
            request.user and request.user.is_authenticated and request.user.role == User.Role.SELLER
        )


class IsCustomer(BasePermission):
    message = "Chỉ Customer mới có quyền thực hiện thao tác này"

    def has_permission(self, request, view) -> bool:
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == User.Role.CUSTOMER
        )


class IsShopOwner(BasePermission):
    message = "Bạn không có quyền truy cập dữ liệu của gian hàng này"

    def has_permission(self, request, view) -> bool:
        return bool(
            request.user and request.user.is_authenticated and request.user.role == User.Role.SELLER
        )

    def has_object_permission(self, request, view, obj) -> bool:
        if isinstance(obj, Shop):
            owner_id = obj.owner_id
        elif isinstance(obj, SellerProfile):
            owner_id = obj.user_id
        elif isinstance(obj, SellerDocument):
            owner_id = obj.seller_profile.user_id
        else:
            return False
        return owner_id == request.user.pk


class IsSellerShopOperational(IsShopOwner):
    message = "Gian hàng đang bị khóa, không thể tạo dữ liệu mới"

    def has_permission(self, request, view) -> bool:
        if not super().has_permission(request, view):
            return False
        return Shop.objects.filter(
            owner=request.user,
            status=Shop.Status.APPROVED,
            is_deleted=False,
        ).exists()


class IsSellerApplicationOwner(BasePermission):
    message = "Bạn không có quyền truy cập hồ sơ seller này"

    def has_permission(self, request, view) -> bool:
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj) -> bool:
        return isinstance(obj, SellerProfile) and obj.user_id == request.user.pk
