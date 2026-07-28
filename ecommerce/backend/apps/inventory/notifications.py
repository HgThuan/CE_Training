from functools import partial

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction

from apps.account.models import Notification

from .models import StockAlert


class InventoryNotificationService:
    """Persist inventory notifications; external email delivery only starts after commit."""

    @staticmethod
    def notify_low_stock(*, balance) -> None:
        variant = balance.variant
        Notification.objects.create(
            user=variant.shop.owner,
            kind=Notification.Kind.INVENTORY_LOW_STOCK,
            title=f"Tồn kho thấp: {variant.sku}",
            message=(
                f"Biến thể {variant.sku} còn {balance.available_stock} sản phẩm, "
                f"ngưỡng cảnh báo là {balance.low_stock_threshold}."
            ),
            metadata={
                "variant_id": str(variant.pk),
                "available_stock": balance.available_stock,
                "low_stock_threshold": balance.low_stock_threshold,
            },
        )

    @staticmethod
    def notify_back_in_stock(*, variant, available_stock: int) -> int:
        alerts = list(
            StockAlert.objects.select_for_update()
            .select_related("user")
            .filter(variant=variant, is_notified=False)
            .order_by("pk")
        )
        if not alerts:
            return 0

        Notification.objects.bulk_create(
            [
                Notification(
                    user=alert.user,
                    kind=Notification.Kind.BACK_IN_STOCK,
                    title=f"{variant.product.name} đã có hàng",
                    message=f"Biến thể {variant.sku} hiện đã có thể đặt mua.",
                    metadata={
                        "variant_id": str(variant.pk),
                        "product_slug": variant.product.slug,
                        "available_stock": available_stock,
                    },
                )
                for alert in alerts
            ]
        )
        StockAlert.objects.filter(pk__in=[alert.pk for alert in alerts]).update(
            is_notified=True
        )
        for alert in alerts:
            transaction.on_commit(
                partial(
                    send_mail,
                    subject=f"{variant.product.name} đã có hàng trở lại",
                    message=f"Biến thể {variant.sku} bạn quan tâm hiện đã có thể đặt mua.",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[alert.user.email],
                    fail_silently=True,
                )
            )
        return len(alerts)

