import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.common.models import TimeStampedModel


class Order(TimeStampedModel):
    class PaymentStatus(models.TextChoices):
        PENDING = "PENDING", "Chờ thanh toán"
        PAID = "PAID", "Đã thanh toán"
        FAILED = "FAILED", "Thanh toán thất bại"
        EXPIRED = "EXPIRED", "Hết hạn thanh toán"
        REFUND_PENDING = "REFUND_PENDING", "Chờ hoàn tiền"
        REFUNDED = "REFUNDED", "Đã hoàn tiền"

    class PaymentMethod(models.TextChoices):
        COD = "COD", "Thanh toán khi nhận hàng"
        VNPAY = "VNPAY", "VNPay"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_code = models.CharField(max_length=40, unique=True, db_index=True)
    customer = models.ForeignKey(
        "account.CustomerProfile", on_delete=models.PROTECT, related_name="orders"
    )
    currency = models.CharField(max_length=3, default="VND")
    subtotal = models.DecimalField(max_digits=18, decimal_places=0)
    platform_discount = models.DecimalField(max_digits=18, decimal_places=0, default=Decimal("0"))
    shop_discount_total = models.DecimalField(max_digits=18, decimal_places=0, default=Decimal("0"))
    shipping_total = models.DecimalField(max_digits=18, decimal_places=0, default=Decimal("0"))
    grand_total = models.DecimalField(max_digits=18, decimal_places=0)
    payment_status = models.CharField(
        max_length=30,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
        db_index=True,
    )
    payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices)
    idempotency_key = models.CharField(max_length=120, unique=True)
    checkout_note = models.TextField(blank=True)
    placed_at = models.DateTimeField(default=timezone.now, db_index=True)
    expires_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        db_table = "orders"
        ordering = ("-created_at",)
        constraints = [
            models.CheckConstraint(condition=Q(subtotal__gte=0), name="order_subtotal_nonnegative"),
            models.CheckConstraint(
                condition=Q(platform_discount__gte=0), name="order_platform_discount_nonnegative"
            ),
            models.CheckConstraint(
                condition=Q(shop_discount_total__gte=0), name="order_shop_discount_nonnegative"
            ),
            models.CheckConstraint(
                condition=Q(shipping_total__gte=0), name="order_shipping_nonnegative"
            ),
            models.CheckConstraint(
                condition=Q(grand_total__gte=0), name="order_grand_total_nonnegative"
            ),
        ]
        indexes = [
            models.Index(fields=("customer", "-created_at"), name="order_customer_created_idx")
        ]

    def __str__(self) -> str:
        return self.order_code


class OrderAddress(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.OneToOneField(Order, on_delete=models.PROTECT, related_name="shipping_address")
    recipient_name = models.CharField(max_length=150)
    recipient_phone = models.CharField(max_length=20)
    province_code = models.CharField(max_length=20, blank=True)
    province_name = models.CharField(max_length=100)
    district_code = models.CharField(max_length=20, blank=True)
    district_name = models.CharField(max_length=100)
    ward_code = models.CharField(max_length=20, blank=True)
    ward_name = models.CharField(max_length=100)
    address_line = models.CharField(max_length=255)

    class Meta:
        db_table = "order_addresses"


class ShopOrder(TimeStampedModel):
    class FulfillmentStatus(models.TextChoices):
        PENDING_CONFIRMATION = "PENDING_CONFIRMATION", "Chờ xác nhận"
        CONFIRMED = "CONFIRMED", "Đã xác nhận"
        PACKING = "PACKING", "Đang đóng gói"
        SHIPPING = "SHIPPING", "Đang giao"
        DELIVERED = "DELIVERED", "Đã giao"
        COMPLETED = "COMPLETED", "Hoàn thành"
        CANCELLED = "CANCELLED", "Đã hủy"
        DELIVERY_FAILED = "DELIVERY_FAILED", "Giao thất bại"
        RETURN_REQUESTED = "RETURN_REQUESTED", "Yêu cầu trả hàng"
        RETURNED = "RETURNED", "Đã trả hàng"
        RETURN_REJECTED = "RETURN_REJECTED", "Từ chối trả hàng"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name="shop_orders")
    shop = models.ForeignKey("account.Shop", on_delete=models.PROTECT, related_name="shop_orders")
    shop_order_code = models.CharField(max_length=45, unique=True, db_index=True)
    fulfillment_status = models.CharField(
        max_length=30,
        choices=FulfillmentStatus.choices,
        default=FulfillmentStatus.PENDING_CONFIRMATION,
        db_index=True,
    )
    subtotal = models.DecimalField(max_digits=18, decimal_places=0)
    shop_discount = models.DecimalField(max_digits=18, decimal_places=0, default=Decimal("0"))
    platform_discount_allocated = models.DecimalField(
        max_digits=18, decimal_places=0, default=Decimal("0")
    )
    shipping_fee = models.DecimalField(max_digits=18, decimal_places=0, default=Decimal("0"))
    total_amount = models.DecimalField(max_digits=18, decimal_places=0)
    shipping_method_code = models.CharField(max_length=50, null=True, blank=True)
    shipping_method_name = models.CharField(max_length=100, null=True, blank=True)
    seller_note = models.TextField(blank=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    cod_collected_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "shop_orders"
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(fields=("order", "shop"), name="shop_order_order_shop_uniq"),
            models.CheckConstraint(
                condition=Q(subtotal__gte=0), name="shop_order_subtotal_nonnegative"
            ),
            models.CheckConstraint(
                condition=Q(total_amount__gte=0), name="shop_order_total_nonnegative"
            ),
        ]
        indexes = [
            models.Index(fields=("shop", "fulfillment_status"), name="shop_order_shop_status_idx"),
            models.Index(
                fields=("fulfillment_status", "created_at"), name="shop_order_status_created_idx"
            ),
        ]

    @property
    def reservation_reference(self) -> str:
        return self.shop_order_code


class OrderItem(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    shop_order = models.ForeignKey(ShopOrder, on_delete=models.PROTECT, related_name="items")
    product = models.ForeignKey(
        "product.Product", on_delete=models.SET_NULL, null=True, related_name="order_items"
    )
    variant = models.ForeignKey(
        "product.ProductVariant", on_delete=models.SET_NULL, null=True, related_name="order_items"
    )
    product_name = models.CharField(max_length=255)
    variant_name = models.CharField(max_length=255, blank=True)
    sku = models.CharField(max_length=100, db_index=True)
    variant_attributes = models.JSONField(default=dict)
    product_image_url = models.URLField(max_length=1000, null=True, blank=True)
    unit_original_price = models.DecimalField(max_digits=18, decimal_places=0)
    unit_sale_price = models.DecimalField(max_digits=18, decimal_places=0)
    quantity = models.PositiveIntegerField()
    line_subtotal = models.DecimalField(max_digits=18, decimal_places=0)
    shop_discount = models.DecimalField(max_digits=18, decimal_places=0, default=Decimal("0"))
    platform_discount = models.DecimalField(max_digits=18, decimal_places=0, default=Decimal("0"))
    line_total = models.DecimalField(max_digits=18, decimal_places=0)
    cost_price_snapshot = models.DecimalField(
        max_digits=18, decimal_places=0, null=True, blank=True
    )

    class Meta:
        db_table = "order_items"
        ordering = ("created_at",)
        constraints = [
            models.CheckConstraint(
                condition=Q(quantity__gt=0), name="order_item_quantity_positive"
            ),
            models.CheckConstraint(
                condition=Q(line_total__gte=0), name="order_item_total_nonnegative"
            ),
        ]


class OrderStatusHistory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    shop_order = models.ForeignKey(
        ShopOrder, on_delete=models.PROTECT, related_name="status_history"
    )
    from_status = models.CharField(max_length=30, blank=True)
    to_status = models.CharField(max_length=30, db_index=True)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="order_status_changes",
    )
    reason = models.TextField(blank=True)
    metadata = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "order_status_histories"
        ordering = ("created_at",)


class OrderCancellation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    shop_order = models.OneToOneField(
        ShopOrder, on_delete=models.PROTECT, related_name="cancellation"
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="order_cancellations"
    )
    reason_code = models.CharField(max_length=50)
    reason_detail = models.TextField(blank=True)
    stock_restored_at = models.DateTimeField(null=True, blank=True)
    voucher_released_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "order_cancellations"


class ShippingFeeRule(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    shop = models.OneToOneField(
        "account.Shop", on_delete=models.CASCADE, related_name="shipping_fee_rule"
    )
    flat_fee = models.DecimalField(max_digits=18, decimal_places=0, default=Decimal("30000"))
    free_shipping_threshold = models.DecimalField(
        max_digits=18, decimal_places=0, null=True, blank=True
    )

    class Meta:
        db_table = "shipping_fee_rules"
        constraints = [
            models.CheckConstraint(
                condition=Q(flat_fee__gte=0), name="shipping_flat_fee_nonnegative"
            ),
            models.CheckConstraint(
                condition=Q(free_shipping_threshold__isnull=True)
                | Q(free_shipping_threshold__gte=0),
                name="shipping_free_threshold_nonnegative",
            ),
        ]

    def calculate(self, subtotal) -> Decimal:
        amount = Decimal(subtotal)
        if self.free_shipping_threshold is not None and amount >= self.free_shipping_threshold:
            return Decimal("0")
        return self.flat_fee
