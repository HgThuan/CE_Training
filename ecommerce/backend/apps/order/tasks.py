import logging

from celery import shared_task
from django.db import transaction
from django.utils import timezone

from apps.account.models import Notification
from apps.inventory.models import StockReservation
from apps.inventory.services import StockService

from .models import Order, ShopOrder
from .services import OrderService

logger = logging.getLogger(__name__)


@shared_task(autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def send_order_confirmation_notification(order_id: str) -> int:
    order = (
        Order.objects.select_related("customer__user")
        .prefetch_related("shop_orders__shop__owner")
        .filter(pk=order_id)
        .first()
    )
    if order is None:
        return 0
    _, customer_created = Notification.objects.get_or_create(
        user=order.customer.user,
        kind=Notification.Kind.ORDER,
        metadata={"event": "order_created", "order_id": str(order.pk)},
        defaults={
            "title": "Đặt hàng thành công",
            "message": f"Đơn {order.order_code} đã được tạo.",
        },
    )
    created_count = int(customer_created)
    for shop_order in order.shop_orders.all():
        _, seller_created = Notification.objects.get_or_create(
            user=shop_order.shop.owner,
            kind=Notification.Kind.ORDER,
            metadata={
                "event": "seller_order_created",
                "shop_order_id": str(shop_order.pk),
            },
            defaults={
                "title": "Bạn có đơn hàng mới",
                "message": f"Đơn {shop_order.shop_order_code} đang chờ xác nhận.",
            },
        )
        created_count += int(seller_created)
    return created_count


@shared_task(autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def send_order_status_change_notification(shop_order_id: str, new_status: str) -> int:
    shop_order = (
        ShopOrder.objects.select_related("order__customer__user").filter(pk=shop_order_id).first()
    )
    if shop_order is None:
        return 0
    _, created = Notification.objects.get_or_create(
        user=shop_order.order.customer.user,
        kind=Notification.Kind.ORDER,
        metadata={
            "event": "order_status_changed",
            "shop_order_id": str(shop_order.pk),
            "status": new_status,
        },
        defaults={
            "title": "Đơn hàng đã cập nhật",
            "message": f"Đơn {shop_order.shop_order_code}: {new_status}.",
        },
    )
    return int(created)


@shared_task(autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def expire_pending_orders() -> int:
    ids = list(
        Order.objects.filter(
            payment_method=Order.PaymentMethod.VNPAY,
            payment_status=Order.PaymentStatus.PENDING,
            expires_at__lt=timezone.now(),
        ).values_list("pk", flat=True)
    )
    expired = 0
    for order_id in ids:
        with transaction.atomic():
            order = (
                Order.objects.select_for_update().select_related("customer__user").get(pk=order_id)
            )
            if order.payment_status != Order.PaymentStatus.PENDING:
                continue
            for shop_order in order.shop_orders.filter(
                fulfillment_status=ShopOrder.FulfillmentStatus.PENDING_CONFIRMATION
            ):
                OrderService.cancel(shop_order, order.customer.user, "PAYMENT_EXPIRED")
            order.payment_status = Order.PaymentStatus.EXPIRED
            order.save(update_fields=("payment_status", "updated_at"))
            order.payments.filter(status="PENDING").update(
                status="EXPIRED", updated_at=timezone.now()
            )
            expired += 1
    return expired


@shared_task(autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def release_expired_stock_reservations() -> int:
    references = list(
        StockReservation.objects.filter(
            status=StockReservation.Status.ACTIVE,
            expires_at__lt=timezone.now(),
        )
        .values_list("order_reference", flat=True)
        .distinct()
    )
    released = 0
    for reference in references:
        shop_order = (
            ShopOrder.objects.select_related("order__customer__user")
            .filter(
                shop_order_code=reference,
                fulfillment_status=ShopOrder.FulfillmentStatus.PENDING_CONFIRMATION,
            )
            .first()
        )
        if shop_order is not None:
            released += len(StockService.release_stock(reference, shop_order.order.customer.user))
    return released
