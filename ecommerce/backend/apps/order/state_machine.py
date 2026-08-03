from apps.account.models import User

from .models import ShopOrder


class OrderStateMachine:
    """Fulfillment transitions. CONFIRMED -> CANCELLED is an explicit Sprint 07 policy."""

    S = ShopOrder.FulfillmentStatus
    TRANSITIONS = {
        S.PENDING_CONFIRMATION: {S.CONFIRMED, S.CANCELLED},
        S.CONFIRMED: {S.PACKING, S.CANCELLED},
        S.PACKING: {S.SHIPPING, S.CANCELLED},
        S.SHIPPING: {S.DELIVERED, S.DELIVERY_FAILED},
        S.DELIVERED: {S.COMPLETED, S.RETURN_REQUESTED},
        S.RETURN_REQUESTED: {S.RETURNED, S.RETURN_REJECTED},
    }
    CUSTOMER_TARGETS = {S.CANCELLED}
    SELLER_TARGETS = {
        S.CONFIRMED,
        S.PACKING,
        S.SHIPPING,
        S.DELIVERED,
        S.COMPLETED,
        S.CANCELLED,
        S.DELIVERY_FAILED,
    }

    @classmethod
    def can_transition(cls, current: str, target: str, actor_role: str) -> bool:
        if target not in cls.TRANSITIONS.get(current, set()):
            return False
        if actor_role == User.Role.ADMIN:
            return True
        if actor_role == User.Role.CUSTOMER:
            return current == cls.S.PENDING_CONFIRMATION and target in cls.CUSTOMER_TARGETS
        if actor_role == User.Role.SELLER:
            return target in cls.SELLER_TARGETS
        return False
