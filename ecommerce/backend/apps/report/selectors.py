from datetime import timedelta
from decimal import Decimal

from django.db.models import Avg, Count, DecimalField, F, Q, Sum, Value
from django.db.models.functions import Coalesce, TruncDay, TruncMonth, TruncWeek
from django.utils import timezone

from apps.account.models import CustomerProfile, Shop
from apps.ai.models import AIRequestLog, ChatFeedback, ChatSession
from apps.order.models import Order, OrderItem, ShopOrder
from apps.product.models import Product

REVENUE_STATUSES = (ShopOrder.FulfillmentStatus.DELIVERED, ShopOrder.FulfillmentStatus.COMPLETED)


def date_range(days: int):
    days = max(1, min(days, 366))
    end = timezone.now()
    return end - timedelta(days=days), end


def revenue_expression(field="total_amount"):
    return Coalesce(Sum(field), Value(Decimal("0")), output_field=DecimalField())


def admin_summary(days=30):
    start, _ = date_range(days)
    completed = ShopOrder.objects.filter(fulfillment_status__in=REVENUE_STATUSES)
    return {
        "revenue": completed.filter(completed_at__gte=start).aggregate(v=revenue_expression())["v"],
        "orders": ShopOrder.objects.filter(created_at__gte=start).count(),
        "customers": CustomerProfile.objects.filter(created_at__gte=start).count(),
        "products": Product.objects.filter(created_at__gte=start, is_deleted=False).count(),
    }


def revenue_chart(days=30, shop=None, period="day"):
    start, _ = date_range(days)

    # Current period data
    queryset = ShopOrder.objects.filter(
        fulfillment_status__in=REVENUE_STATUSES, completed_at__gte=start
    )
    if shop is not None:
        queryset = queryset.filter(shop=shop)

    current_revenue = queryset.aggregate(v=revenue_expression())["v"]

    # Prior period data
    prior_start, prior_end = start - timedelta(days=days), start
    prior_qs = ShopOrder.objects.filter(
        fulfillment_status__in=REVENUE_STATUSES,
        completed_at__gte=prior_start,
        completed_at__lt=prior_end,
    )
    if shop is not None:
        prior_qs = prior_qs.filter(shop=shop)
    prior_revenue = prior_qs.aggregate(v=revenue_expression())["v"]

    # Growth percentage
    if prior_revenue > 0:
        growth = round((current_revenue - prior_revenue) / prior_revenue * 100, 2)
    elif current_revenue > 0:
        growth = 100.0
    else:
        growth = 0.0

    trunc_func = TruncDay
    if period == "week":
        trunc_func = TruncWeek
    elif period == "month":
        trunc_func = TruncMonth

    rows = (
        queryset.annotate(group=trunc_func("completed_at"))
        .values("group")
        .annotate(revenue=revenue_expression(), orders=Count("id"))
        .order_by("group")
    )

    return {
        "current_revenue": current_revenue,
        "prior_revenue": prior_revenue,
        "growth": float(growth),
        "chart": [
            {
                "date": row["group"].date() if hasattr(row["group"], "date") else row["group"],
                "revenue": row["revenue"],
                "orders": row["orders"],
            }
            for row in rows
        ],
    }


def top_products(days=30, shop=None, limit=10):
    start, _ = date_range(days)
    queryset = OrderItem.objects.filter(
        shop_order__fulfillment_status__in=REVENUE_STATUSES,
        shop_order__completed_at__gte=start,
    )
    if shop is not None:
        queryset = queryset.filter(shop_order__shop=shop)
    return list(
        queryset.values("product_id", "product_name")
        .annotate(quantity=Sum("quantity"), revenue=revenue_expression("line_total"))
        .order_by("-quantity", "product_name")[:limit]
    )


def seller_summary(shop, days=30):
    start, _ = date_range(days)
    orders = ShopOrder.objects.filter(shop=shop, created_at__gte=start)
    return {
        "shop_id": shop.pk,
        "shop_name": shop.name,
        "revenue": orders.filter(fulfillment_status__in=REVENUE_STATUSES).aggregate(
            v=revenue_expression()
        )["v"],
        "orders": orders.count(),
        "pending_orders": orders.filter(
            fulfillment_status=ShopOrder.FulfillmentStatus.PENDING_CONFIRMATION
        ).count(),
        "products": Product.objects.filter(shop=shop, is_deleted=False).count(),
    }


def top_sellers(days=30, limit=10):
    start, _ = date_range(days)
    return list(
        Shop.objects.filter(
            shop_orders__completed_at__gte=start,
            shop_orders__fulfillment_status__in=REVENUE_STATUSES,
        )
        .values("id", "name")
        .annotate(
            revenue=revenue_expression("shop_orders__total_amount"),
            orders=Count("shop_orders", distinct=True),
        )
        .order_by("-revenue")[:limit]
    )


def top_customers(days=30, limit=10):
    start, _ = date_range(days)
    return list(
        Order.objects.filter(
            placed_at__gte=start, shop_orders__fulfillment_status__in=REVENUE_STATUSES
        )
        .values("customer_id", email=F("customer__user__email"))
        .annotate(
            spending=revenue_expression("shop_orders__total_amount"),
            orders=Count("id", distinct=True),
        )
        .order_by("-spending")[:limit]
    )


def top_categories(days=30, limit=10):
    start, _ = date_range(days)
    return list(
        OrderItem.objects.filter(
            shop_order__completed_at__gte=start, shop_order__fulfillment_status__in=REVENUE_STATUSES
        )
        .values("product__category_id", name=F("product__category__name"))
        .annotate(quantity=Sum("quantity"), revenue=revenue_expression("line_total"))
        .order_by("-quantity")[:limit]
    )


def cancel_return_rate(days=30):
    start, _ = date_range(days)
    queryset = ShopOrder.objects.filter(created_at__gte=start)
    total = queryset.count()
    cancelled = queryset.filter(fulfillment_status=ShopOrder.FulfillmentStatus.CANCELLED).count()
    returned = queryset.filter(fulfillment_status=ShopOrder.FulfillmentStatus.RETURNED).count()
    divisor = total or 1
    return {
        "total_orders": total,
        "cancelled": cancelled,
        "returned": returned,
        "cancel_rate": round(cancelled * 100 / divisor, 2),
        "return_rate": round(returned * 100 / divisor, 2),
    }


def chatbot_metrics(days=30):
    start, _ = date_range(days)
    sessions = ChatSession.objects.filter(created_at__gte=start)
    total_sessions = sessions.count()
    escalated_sessions = sessions.filter(status=ChatSession.Status.ESCALATED).count()
    feedback = ChatFeedback.objects.filter(created_at__gte=start)
    feedback_count = feedback.count()
    resolved_feedback = feedback.filter(resolved=True).count()
    unresolved_feedback = feedback.filter(resolved=False).count()
    outcome_count = feedback_count + escalated_sessions
    chat_logs = AIRequestLog.objects.filter(
        feature=AIRequestLog.Feature.CHAT_TURN,
        created_at__gte=start,
    )
    variant_rows = sessions.values("experiment_variant").annotate(
        sessions=Count("id", distinct=True),
        escalated=Count(
            "id",
            filter=Q(status=ChatSession.Status.ESCALATED),
            distinct=True,
        ),
        feedback_count=Count("feedback_entries", distinct=True),
        csat=Avg("feedback_entries__rating"),
    )
    return {
        "sessions": total_sessions,
        "handoffs": escalated_sessions,
        "handoff_rate": round(escalated_sessions * 100 / (total_sessions or 1), 2),
        "automated_resolution_rate": round(resolved_feedback * 100 / (outcome_count or 1), 2),
        "average_response_ms": round(chat_logs.aggregate(value=Avg("latency_ms"))["value"] or 0),
        "feedback_count": feedback_count,
        "feedback_rate": round(feedback_count * 100 / (total_sessions or 1), 2),
        "csat": round(feedback.aggregate(value=Avg("rating"))["value"] or 0, 2),
        "resolved_feedback": resolved_feedback,
        "unresolved_feedback": unresolved_feedback,
        "variants": [
            {
                **row,
                "csat": round(row["csat"] or 0, 2),
                "handoff_rate": round(row["escalated"] * 100 / (row["sessions"] or 1), 2),
            }
            for row in variant_rows.order_by("experiment_variant")
        ],
    }
