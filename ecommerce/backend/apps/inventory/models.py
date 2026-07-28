from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from apps.common.models import TimeStampedModel


class InventoryBalance(TimeStampedModel):
    variant = models.OneToOneField(
        "product.ProductVariant",
        on_delete=models.CASCADE,
        related_name="inventory_balance",
    )
    available_stock = models.IntegerField(default=0)
    reserved_stock = models.IntegerField(default=0)
    low_stock_threshold = models.IntegerField(default=5)

    class Meta:
        ordering = ("variant__sku",)
        constraints = [
            models.CheckConstraint(
                condition=Q(available_stock__gte=0),
                name="inventory_available_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(reserved_stock__gte=0),
                name="inventory_reserved_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(low_stock_threshold__gte=0),
                name="inventory_threshold_nonnegative",
            ),
        ]
        indexes = [
            models.Index(fields=("created_at",), name="inventory_balance_created_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.variant.sku}: {self.available_stock} available"


class StockMovement(TimeStampedModel):
    class MovementType(models.TextChoices):
        IN = "in", "Nhập kho"
        OUT = "out", "Xuất kho"
        ADJUSTMENT = "adjustment", "Điều chỉnh"
        RESERVE = "reserve", "Giữ kho"
        RELEASE = "release", "Hoàn giữ kho"
        COMMIT = "commit", "Chốt bán"

    class Bucket(models.TextChoices):
        AVAILABLE = "available", "Khả dụng"
        RESERVED = "reserved", "Đã giữ"

    class ReferenceType(models.TextChoices):
        STOCK_ENTRY = "stock_entry", "Phiếu nhập"
        STOCK_OUT = "stock_out", "Phiếu xuất"
        ADJUSTMENT = "adjustment", "Kiểm kê"
        ORDER = "order", "Đơn hàng"

    variant = models.ForeignKey(
        "product.ProductVariant",
        on_delete=models.PROTECT,
        related_name="stock_movements",
    )
    movement_type = models.CharField(
        max_length=20,
        choices=MovementType.choices,
        db_index=True,
    )
    bucket = models.CharField(max_length=20, choices=Bucket.choices)
    quantity = models.IntegerField()
    balance_after = models.IntegerField()
    reference_type = models.CharField(max_length=20, choices=ReferenceType.choices)
    reference_id = models.CharField(max_length=64)
    note = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="stock_movements",
    )

    class Meta:
        ordering = ("-created_at", "-id")
        constraints = [
            models.CheckConstraint(
                condition=~Q(quantity=0),
                name="stock_movement_quantity_nonzero",
            ),
            models.CheckConstraint(
                condition=Q(balance_after__gte=0),
                name="stock_movement_balance_nonnegative",
            ),
        ]
        indexes = [
            models.Index(
                fields=("variant", "-created_at"),
                name="stock_move_variant_created_idx",
            ),
            models.Index(fields=("created_at",), name="stock_move_created_idx"),
            models.Index(
                fields=("reference_type", "reference_id"),
                name="stock_move_reference_idx",
            ),
        ]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError("StockMovement là ledger append-only và không thể cập nhật")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("StockMovement là ledger append-only và không thể xóa")


class StockEntry(TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Bản nháp"
        CONFIRMED = "confirmed", "Đã xác nhận"

    shop = models.ForeignKey(
        "account.Shop",
        on_delete=models.PROTECT,
        related_name="stock_entries",
    )
    supplier_name = models.CharField(max_length=255)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
    )
    note = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_stock_entries",
    )
    confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="confirmed_stock_entries",
        null=True,
        blank=True,
    )
    confirmed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(status="draft", confirmed_by__isnull=True, confirmed_at__isnull=True)
                    | Q(
                        status="confirmed",
                        confirmed_by__isnull=False,
                        confirmed_at__isnull=False,
                    )
                ),
                name="stock_entry_confirmation_valid",
            ),
        ]
        indexes = [
            models.Index(fields=("shop", "status"), name="stock_entry_shop_status_idx"),
            models.Index(fields=("created_at",), name="stock_entry_created_idx"),
        ]


class StockEntryItem(TimeStampedModel):
    stock_entry = models.ForeignKey(
        StockEntry,
        on_delete=models.CASCADE,
        related_name="items",
    )
    variant = models.ForeignKey(
        "product.ProductVariant",
        on_delete=models.PROTECT,
        related_name="stock_entry_items",
    )
    quantity = models.IntegerField()
    unit_cost = models.DecimalField(max_digits=18, decimal_places=0)

    class Meta:
        ordering = ("created_at", "id")
        constraints = [
            models.CheckConstraint(
                condition=Q(quantity__gt=0),
                name="stock_entry_item_quantity_positive",
            ),
            models.CheckConstraint(
                condition=Q(unit_cost__gte=0),
                name="stock_entry_item_cost_nonnegative",
            ),
            models.UniqueConstraint(
                fields=("stock_entry", "variant"),
                name="stock_entry_variant_unique",
            ),
        ]


class StockOutEntry(TimeStampedModel):
    class EntryType(models.TextChoices):
        OUT = "out", "Xuất kho"
        ADJUSTMENT = "adjustment", "Kiểm kê"

    class Status(models.TextChoices):
        DRAFT = "draft", "Bản nháp"
        CONFIRMED = "confirmed", "Đã xác nhận"

    shop = models.ForeignKey(
        "account.Shop",
        on_delete=models.PROTECT,
        related_name="stock_out_entries",
    )
    entry_type = models.CharField(max_length=20, choices=EntryType.choices)
    reason = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_stock_out_entries",
    )
    confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="confirmed_stock_out_entries",
        null=True,
        blank=True,
    )
    confirmed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(status="draft", confirmed_by__isnull=True, confirmed_at__isnull=True)
                    | Q(
                        status="confirmed",
                        confirmed_by__isnull=False,
                        confirmed_at__isnull=False,
                    )
                ),
                name="stock_out_confirmation_valid",
            ),
        ]
        indexes = [
            models.Index(fields=("shop", "status"), name="stock_out_shop_status_idx"),
            models.Index(fields=("created_at",), name="stock_out_created_idx"),
        ]


class StockOutEntryItem(TimeStampedModel):
    stock_out_entry = models.ForeignKey(
        StockOutEntry,
        on_delete=models.CASCADE,
        related_name="items",
    )
    variant = models.ForeignKey(
        "product.ProductVariant",
        on_delete=models.PROTECT,
        related_name="stock_out_entry_items",
    )
    # OUT uses a positive amount; ADJUSTMENT stores the new physical count and may be zero.
    quantity = models.IntegerField()

    class Meta:
        ordering = ("created_at", "id")
        constraints = [
            models.CheckConstraint(
                condition=Q(quantity__gte=0),
                name="stock_out_item_quantity_nonnegative",
            ),
            models.UniqueConstraint(
                fields=("stock_out_entry", "variant"),
                name="stock_out_entry_variant_unique",
            ),
        ]


class StockReservation(TimeStampedModel):
    class Status(models.TextChoices):
        ACTIVE = "active", "Đang giữ"
        RELEASED = "released", "Đã hoàn"
        COMMITTED = "committed", "Đã chốt"
        EXPIRED = "expired", "Hết hạn"

    variant = models.ForeignKey(
        "product.ProductVariant",
        on_delete=models.PROTECT,
        related_name="stock_reservations",
    )
    order_reference = models.CharField(max_length=64)
    quantity = models.IntegerField()
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True,
    )
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.CheckConstraint(
                condition=Q(quantity__gt=0),
                name="stock_reservation_quantity_positive",
            ),
            models.UniqueConstraint(
                fields=("variant", "order_reference"),
                name="stock_reservation_variant_order_unique",
            ),
        ]
        indexes = [
            models.Index(
                fields=("order_reference", "status"),
                name="stock_res_order_status_idx",
            ),
            models.Index(fields=("expires_at",), name="stock_reservation_expiry_idx"),
            models.Index(fields=("created_at",), name="stock_reservation_created_idx"),
        ]


class StockAlert(TimeStampedModel):
    variant = models.ForeignKey(
        "product.ProductVariant",
        on_delete=models.CASCADE,
        related_name="stock_alerts",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="stock_alerts",
    )
    is_notified = models.BooleanField(default=False, db_index=True)

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=("variant", "user"),
                name="stock_alert_variant_user_unique",
            ),
        ]
        indexes = [
            models.Index(
                fields=("variant", "is_notified"),
                name="stock_alert_variant_idx",
            ),
            models.Index(fields=("created_at",), name="stock_alert_created_idx"),
        ]
