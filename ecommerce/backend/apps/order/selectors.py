from django.db.models import Count, Max, Q, Sum

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
        .prefetch_related(
            "shop_orders__shop",
            "shop_orders__items__review",
            "shop_orders__items__review__media",
            "shop_orders__status_history",
        )
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


def get_customers_for_seller(user, *, search=None):
    shop = Shop.objects.filter(owner=user, is_deleted=False).first()
    if shop is None:
        return ShopOrder.objects.none().values("order__customer__user_id")
    queryset = (
        ShopOrder.objects.filter(shop=shop)
        .exclude(
            fulfillment_status__in=(
                ShopOrder.FulfillmentStatus.CANCELLED,
                ShopOrder.FulfillmentStatus.DELIVERY_FAILED,
            )
        )
        .values(
            "order__customer__user_id",
            "order__customer__user__email",
            "order__customer__user__full_name",
        )
        .annotate(
            order_count=Count("id", distinct=True),
            total_spent=Sum("total_amount"),
            last_order_at=Max("created_at"),
        )
        .order_by("-last_order_at")
    )
    if search:
        queryset = queryset.filter(
            Q(order__customer__user__email__icontains=search)
            | Q(order__customer__user__full_name__icontains=search)
        )
    return queryset


def get_customer_orders_for_seller(user, customer_id):
    shop = Shop.objects.filter(owner=user, is_deleted=False).first()
    if shop is None:
        return ShopOrder.objects.none()
    return (
        ShopOrder.objects.filter(shop=shop, order__customer__user_id=customer_id)
        .select_related("order__customer__user", "order__shipping_address", "shop")
        .prefetch_related("items", "status_history")
        .order_by("-created_at")
    )
