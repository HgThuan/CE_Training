import uuid
from decimal import Decimal

from django.db import models
from django.db.models import F, Q
from django.utils import timezone

from apps.common.models import TimeStampedModel


class Voucher(TimeStampedModel):
    class Scope(models.TextChoices):
        PLATFORM = "platform", "Sàn"
        SHOP = "shop", "Shop"

    class DiscountType(models.TextChoices):
        PERCENTAGE = "percent", "Phần trăm"
        FIXED_AMOUNT = "fixed", "Số tiền cố định"
        FREESHIP = "freeship", "Miễn phí vận chuyển"

    class CollectType(models.TextChoices):
        MANUAL = "manual", "Người dùng lưu"
        AUTO = "auto", "Tự động cấp"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    scope = models.CharField(
        max_length=20,
        choices=Scope.choices,
        db_index=True,
        db_column="issuer_type",
    )
    shop = models.ForeignKey(
        "account.Shop",
        on_delete=models.CASCADE,
        related_name="vouchers",
        null=True,
        blank=True,
        db_column="issuer_id",
    )
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    discount_type = models.CharField(max_length=20, choices=DiscountType.choices)
    discount_value = models.DecimalField(max_digits=18, decimal_places=0, db_column="value")
    max_discount_amount = models.DecimalField(
        max_digits=18,
        decimal_places=0,
        null=True,
        blank=True,
    )
    min_order_amount = models.DecimalField(
        max_digits=18,
        decimal_places=0,
        default=Decimal("0"),
        db_column="min_order_value",
    )
    total_usage_limit = models.PositiveIntegerField(
        null=True,
        blank=True,
        db_column="total_quantity",
    )
    remaining_quantity = models.PositiveIntegerField(null=True, blank=True)
    usage_limit_per_user = models.PositiveIntegerField(default=1, db_column="per_user_limit")
    valid_from = models.DateTimeField(db_column="start_time")
    valid_until = models.DateTimeField(db_column="end_time")
    collect_type = models.CharField(
        max_length=20,
        choices=CollectType.choices,
        default=CollectType.MANUAL,
    )
    stackable_with = models.JSONField(default=list, blank=True)
    applicable_scope = models.JSONField(null=True, blank=True)
    applicable_category = models.ForeignKey(
        "catalog.Category",
        on_delete=models.SET_NULL,
        related_name="vouchers",
        null=True,
        blank=True,
    )
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        db_table = "voucher_campaign"
        ordering = ("-created_at",)
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(scope="platform", shop__isnull=True) | Q(scope="shop", shop__isnull=False)
                ),
                name="voucher_scope_shop_consistent",
            ),
            models.CheckConstraint(
                condition=Q(discount_value__gt=0),
                name="voucher_discount_positive",
            ),
            models.CheckConstraint(
                condition=Q(max_discount_amount__isnull=True) | Q(max_discount_amount__gte=0),
                name="voucher_max_discount_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(min_order_amount__gte=0),
                name="voucher_min_order_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(usage_limit_per_user__gt=0),
                name="voucher_per_user_limit_positive",
            ),
            models.CheckConstraint(
                condition=Q(remaining_quantity__isnull=True) | Q(remaining_quantity__gte=0),
                name="voucher_remaining_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(valid_from__lt=F("valid_until")),
                name="voucher_valid_time_range",
            ),
        ]
        indexes = [
            models.Index(fields=("valid_from", "valid_until"), name="voucher_valid_window_idx"),
            models.Index(
                fields=("scope", "is_active", "valid_from", "valid_until"),
                name="voucher_active_scope_idx",
            ),
        ]

    def save(self, *args, **kwargs) -> None:
        self.code = self.code.strip().upper()
        super().save(*args, **kwargs)

    @property
    def is_valid_now(self) -> bool:
        now = timezone.now()
        return self.is_active and self.valid_from <= now <= self.valid_until

    def __str__(self) -> str:
        return self.code

    @property
    def issued_quantity(self) -> int | None:
        if self.total_usage_limit is None or self.remaining_quantity is None:
            return None
        return self.total_usage_limit - self.remaining_quantity


class UserVoucher(TimeStampedModel):
    class Status(models.TextChoices):
        SAVED = "saved", "Đã lưu"
        PENDING_USE = "pending_use", "Đang khóa"
        USED = "used", "Đã dùng"
        EXPIRED = "expired", "Hết hạn"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        "account.CustomerProfile",
        on_delete=models.PROTECT,
        related_name="user_vouchers",
    )
    voucher_campaign = models.ForeignKey(
        Voucher,
        on_delete=models.PROTECT,
        related_name="user_vouchers",
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SAVED)
    idempotency_key = models.CharField(max_length=128)
    claimed_at = models.DateTimeField(default=timezone.now)
    used_at = models.DateTimeField(null=True, blank=True)
    order_id = models.CharField(max_length=64, null=True, blank=True)
    checkout_token = models.UUIDField(null=True, blank=True, db_index=True)
    pending_expires_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        db_table = "user_voucher"
        ordering = ("-claimed_at", "-id")
        constraints = [
            models.UniqueConstraint(
                fields=("user", "idempotency_key"),
                name="user_voucher_collect_idempotent",
            ),
        ]
        indexes = [
            models.Index(
                fields=("user", "status", "voucher_campaign"),
                name="user_voucher_owner_status_idx",
            ),
        ]


class VoucherEvent(TimeStampedModel):
    class Action(models.TextChoices):
        COLLECT = "collect", "Lưu"
        APPLY = "apply", "Áp dụng"
        USE = "use", "Sử dụng"
        ROLLBACK = "rollback", "Hoàn tác"
        EXPIRE = "expire", "Hết hạn"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_voucher = models.ForeignKey(
        UserVoucher,
        on_delete=models.PROTECT,
        related_name="events",
    )
    action = models.CharField(max_length=20, choices=Action.choices, db_index=True)
    order_id = models.CharField(max_length=64, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ("-created_at", "-id")


class VoucherUsage(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    voucher = models.ForeignKey(Voucher, on_delete=models.PROTECT, related_name="usages")
    user = models.ForeignKey(
        "account.CustomerProfile",
        on_delete=models.PROTECT,
        related_name="voucher_usages",
    )
    order_reference = models.CharField(max_length=64)
    discount_amount = models.DecimalField(max_digits=18, decimal_places=0)
    used_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ("-used_at",)
        constraints = [
            models.UniqueConstraint(
                fields=("voucher", "user", "order_reference"),
                name="voucher_usage_checkout_uniq",
            ),
            models.CheckConstraint(
                condition=Q(discount_amount__gte=0),
                name="voucher_usage_discount_nonnegative",
            ),
        ]
        indexes = [
            models.Index(fields=("voucher", "user"), name="voucher_usage_user_idx"),
        ]


class FlashSale(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ("start_time", "id")
        constraints = [
            models.CheckConstraint(
                condition=Q(start_time__lt=F("end_time")),
                name="flash_sale_valid_time_range",
            ),
        ]
        indexes = [
            models.Index(fields=("start_time", "end_time"), name="flash_sale_window_idx"),
            models.Index(
                fields=("is_active", "start_time", "end_time"),
                name="flash_sale_active_idx",
            ),
        ]

    @property
    def status(self) -> str:
        now = timezone.now()
        if now < self.start_time:
            return "upcoming"
        if now <= self.end_time:
            return "ongoing"
        return "ended"

    def __str__(self) -> str:
        return self.name


class FlashSaleItem(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    flash_sale = models.ForeignKey(
        FlashSale,
        on_delete=models.CASCADE,
        related_name="items",
    )
    variant = models.ForeignKey(
        "product.ProductVariant",
        on_delete=models.PROTECT,
        related_name="flash_sale_items",
    )
    sale_price = models.DecimalField(max_digits=18, decimal_places=0)
    quota = models.PositiveIntegerField()
    sold_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("created_at", "id")
        constraints = [
            models.UniqueConstraint(
                fields=("flash_sale", "variant"),
                name="flash_sale_item_variant_uniq",
            ),
            models.CheckConstraint(
                condition=Q(sale_price__gte=0),
                name="flash_sale_item_price_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(quota__gt=0),
                name="flash_sale_item_quota_positive",
            ),
            models.CheckConstraint(
                condition=Q(sold_count__lte=F("quota")),
                name="flash_sale_item_sold_within_quota",
            ),
        ]

    @property
    def remaining_quota(self) -> int:
        return max(0, self.quota - self.sold_count)
