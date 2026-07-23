from rest_framework.permissions import BasePermission

from .models import User


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
