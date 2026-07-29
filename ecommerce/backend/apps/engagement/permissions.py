from rest_framework.permissions import BasePermission

from apps.account.models import User


def _is_active_role(user, role: str) -> bool:
    return bool(
        user
        and getattr(user, "is_authenticated", False)
        and getattr(user, "is_active", False)
        and not getattr(user, "is_deleted", True)
        and getattr(user, "role", None) == role
    )


class IsActiveCustomer(BasePermission):
    message = "Chỉ Customer đang hoạt động mới có thể thực hiện thao tác này"

    def has_permission(self, request, view) -> bool:
        return _is_active_role(request.user, User.Role.CUSTOMER)


class IsActiveSeller(BasePermission):
    message = "Chỉ Seller đang hoạt động mới có thể trả lời câu hỏi"

    def has_permission(self, request, view) -> bool:
        return _is_active_role(request.user, User.Role.SELLER)
