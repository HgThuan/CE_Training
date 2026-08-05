from apps.account.models import Shop

from .models import Dispute, ReturnRequest

RETURN_GRAPH = (
    "customer",
    "shop_order__shop",
    "shop_order__order",
)


def return_request_graph():
    return ReturnRequest.objects.select_related(*RETURN_GRAPH).prefetch_related(
        "items__order_item", "media"
    )


def get_return_requests_for_customer(user):
    return return_request_graph().filter(customer=user)


def get_return_requests_for_seller(user, *, status=None):
    shop = Shop.objects.filter(owner=user, is_deleted=False).first()
    queryset = (
        return_request_graph().none()
        if shop is None
        else return_request_graph().filter(shop_order__shop=shop)
    )
    if status:
        queryset = queryset.filter(status=status)
    return queryset


def dispute_graph():
    return Dispute.objects.select_related(
        "assigned_admin",
        "opened_by",
        "shop_order__shop",
        "return_request__customer",
        "return_request__shop_order__shop",
        "return_request__shop_order__order",
    ).prefetch_related(
        "evidence__submitted_by", "return_request__items__order_item", "return_request__media"
    )


def get_disputes_for_admin(*, status=None):
    queryset = dispute_graph()
    if status:
        queryset = queryset.filter(status=status)
    return queryset
