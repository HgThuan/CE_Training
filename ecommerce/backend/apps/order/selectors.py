from django.db.models import Q

from apps.account.models import Shop

from .models import Order, ShopOrder

ORDER_GRAPH = (
    "customer__user",
    "shipping_address",
)


def get_orders_for_customer(user, *, status=None):
    queryset = (
        Order.objects.filter(customer__user=user)
        .select_related(*ORDER_GRAPH)
        .prefetch_related("shop_orders__shop", "shop_orders__items", "shop_orders__status_history")
    )
    if status:
        queryset = queryset.filter(shop_orders__fulfillment_status=status).distinct()
    return queryset


def get_shop_orders_for_seller(user, *, status=None):
    shop = Shop.objects.filter(owner=user, is_deleted=False).first()
    queryset = ShopOrder.objects.none()
    if shop is not None:
        queryset = (
            ShopOrder.objects.filter(shop=shop)
            .select_related("order__customer__user", "order__shipping_address", "shop")
            .prefetch_related("items", "status_history")
        )
    if status:
        queryset = queryset.filter(fulfillment_status=status)
    return queryset


def get_all_orders_for_admin(
    *, status=None, seller=None, date_from=None, date_to=None, search=None
):
    queryset = Order.objects.select_related(*ORDER_GRAPH).prefetch_related(
        "shop_orders__shop", "shop_orders__items", "shop_orders__status_history"
    )
    if status:
        queryset = queryset.filter(shop_orders__fulfillment_status=status).distinct()
    if seller:
        queryset = queryset.filter(shop_orders__shop_id=seller).distinct()
    if date_from:
        queryset = queryset.filter(created_at__date__gte=date_from)
    if date_to:
        queryset = queryset.filter(created_at__date__lte=date_to)
    if search:
        queryset = queryset.filter(
            Q(order_code__icontains=search)
            | Q(customer__user__email__icontains=search)
            | Q(customer__user__full_name__icontains=search)
        ).distinct()
    return queryset
