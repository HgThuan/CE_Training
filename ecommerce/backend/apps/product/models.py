import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import F, Q

from apps.common.models import TimeStampedModel


class Product(TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Bản nháp"
        PENDING_REVIEW = "pending_review", "Chờ duyệt"
        APPROVED = "approved", "Đã duyệt"
        REJECTED = "rejected", "Bị từ chối"
        HIDDEN = "hidden", "Đã ẩn"
        SUSPENDED = "suspended", "Tạm ngưng"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    shop = models.ForeignKey(
        "account.Shop",
        on_delete=models.CASCADE,
        related_name="products",
        db_index=True,
    )
    category = models.ForeignKey(
        "catalog.Category",
        on_delete=models.PROTECT,
        related_name="products",
        db_index=True,
    )
    brand = models.ForeignKey(
        "catalog.Brand",
        on_delete=models.SET_NULL,
        related_name="products",
        null=True,
        blank=True,
        db_index=True,
    )
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=280, db_index=False)
    short_description = models.TextField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
    )
    rejection_reason = models.TextField(null=True, blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="approved_products",
        null=True,
        blank=True,
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    rating_average = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=Decimal("0"),
    )
    rating_count = models.PositiveIntegerField(default=0)
    sold_count = models.PositiveBigIntegerField(default=0)
    min_price = models.DecimalField(
        max_digits=18,
        decimal_places=0,
        null=True,
        blank=True,
    )
    max_price = models.DecimalField(
        max_digits=18,
        decimal_places=0,
        null=True,
        blank=True,
    )
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    attribute_values = models.ManyToManyField(
        "AttributeValue",
        through="ProductAttributeValue",
        related_name="products",
    )

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=("shop", "slug"),
                condition=Q(is_deleted=False),
                name="product_shop_slug_active_uniq",
            ),
            models.CheckConstraint(
                condition=Q(min_price__isnull=True) | Q(min_price__gte=0),
                name="product_min_price_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(max_price__isnull=True) | Q(max_price__gte=0),
                name="product_max_price_nonnegative",
            ),
            models.CheckConstraint(
                condition=(
                    Q(min_price__isnull=True)
                    | Q(max_price__isnull=True)
                    | Q(min_price__lte=F("max_price"))
                ),
                name="product_price_range_valid",
            ),
            models.CheckConstraint(
                condition=Q(rating_average__gte=0) & Q(rating_average__lte=5),
                name="product_rating_range_valid",
            ),
        ]
        indexes = [
            models.Index(
                fields=("status", "-created_at"),
                condition=Q(is_deleted=False),
                name="ix_products_public_feed",
            ),
            models.Index(fields=("created_at",), name="product_created_idx"),
            models.Index(fields=("updated_at",), name="product_updated_idx"),
        ]

    def __str__(self) -> str:
        return self.name


class Attribute(TimeStampedModel):
    class DisplayType(models.TextChoices):
        TEXT = "text", "Văn bản"
        COLOR = "color", "Màu sắc"
        IMAGE = "image", "Hình ảnh"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    shop = models.ForeignKey(
        "account.Shop",
        on_delete=models.CASCADE,
        related_name="attributes",
        null=True,
        blank=True,
        db_index=True,
    )
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=100)
    display_type = models.CharField(
        max_length=20,
        choices=DisplayType.choices,
        default=DisplayType.TEXT,
    )
    sort_order = models.IntegerField(default=0)

    class Meta:
        ordering = ("sort_order", "name", "id")
        constraints = [
            models.UniqueConstraint(
                fields=("shop", "name"),
                condition=Q(shop__isnull=False),
                name="attribute_shop_name_uniq",
            ),
            models.UniqueConstraint(
                fields=("name",),
                condition=Q(shop__isnull=True),
                name="attribute_global_name_uniq",
            ),
            models.UniqueConstraint(
                fields=("shop", "code"),
                condition=Q(shop__isnull=False),
                name="attribute_shop_code_uniq",
            ),
            models.UniqueConstraint(
                fields=("code",),
                condition=Q(shop__isnull=True),
                name="attribute_global_code_uniq",
            ),
        ]

    def __str__(self) -> str:
        return self.name


class AttributeValue(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    attribute = models.ForeignKey(
        Attribute,
        on_delete=models.CASCADE,
        related_name="values",
        db_index=True,
    )
    value = models.CharField(max_length=120)
    display_value = models.CharField(max_length=120, null=True, blank=True)
    color_code = models.CharField(max_length=20, null=True, blank=True)
    sort_order = models.IntegerField(default=0)

    class Meta:
        ordering = ("sort_order", "value", "id")
        constraints = [
            models.UniqueConstraint(
                fields=("attribute", "value"),
                name="attribute_value_uniq",
            ),
        ]

    def __str__(self) -> str:
        return self.display_value or self.value


class ProductAttributeValue(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="product_attribute_links",
        db_index=True,
    )
    attribute_value = models.ForeignKey(
        AttributeValue,
        on_delete=models.CASCADE,
        related_name="product_links",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("product", "attribute_value"),
                name="product_attribute_value_uniq",
            ),
        ]


class ProductVariant(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="variants",
        db_index=True,
    )
    shop = models.ForeignKey(
        "account.Shop",
        on_delete=models.CASCADE,
        related_name="product_variants",
        db_index=True,
    )
    sku = models.CharField(max_length=100)
    barcode = models.CharField(max_length=100, null=True, blank=True)
    name = models.CharField(max_length=255, null=True, blank=True)
    original_price = models.DecimalField(max_digits=18, decimal_places=0)
    sale_price = models.DecimalField(max_digits=18, decimal_places=0)
    cost_price = models.DecimalField(
        max_digits=18,
        decimal_places=0,
        null=True,
        blank=True,
    )
    stock_quantity = models.PositiveIntegerField(default=0)
    weight_grams = models.IntegerField(null=True, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    attribute_values = models.ManyToManyField(
        AttributeValue,
        through="VariantAttributeValue",
        related_name="variants",
    )

    class Meta:
        ordering = ("created_at", "id")
        constraints = [
            models.UniqueConstraint(
                fields=("shop", "sku"),
                name="variant_shop_sku_uniq",
            ),
            models.UniqueConstraint(
                fields=("shop", "barcode"),
                condition=Q(barcode__isnull=False),
                name="variant_shop_barcode_uniq",
            ),
            models.CheckConstraint(
                condition=Q(original_price__gte=0),
                name="variant_original_price_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(sale_price__gte=0),
                name="variant_sale_price_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(cost_price__isnull=True) | Q(cost_price__gte=0),
                name="variant_cost_price_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(weight_grams__isnull=True) | Q(weight_grams__gt=0),
                name="variant_weight_positive",
            ),
            models.CheckConstraint(
                condition=Q(original_price=0) | Q(sale_price__lte=F("original_price")),
                name="variant_sale_not_above_original",
            ),
        ]

    def __str__(self) -> str:
        return self.sku


class VariantAttributeValue(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.CASCADE,
        related_name="variant_attribute_links",
        db_index=True,
    )
    attribute = models.ForeignKey(
        Attribute,
        on_delete=models.CASCADE,
        related_name="variant_links",
    )
    attribute_value = models.ForeignKey(
        AttributeValue,
        on_delete=models.CASCADE,
        related_name="variant_links",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("variant", "attribute"),
                name="variant_attribute_uniq",
            ),
            models.UniqueConstraint(
                fields=("variant", "attribute_value"),
                name="variant_attribute_value_uniq",
            ),
        ]


class ProductMedia(TimeStampedModel):
    class MediaType(models.TextChoices):
        IMAGE = "image", "Hình ảnh"
        VIDEO = "video", "Video"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="media",
        db_index=True,
    )
    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.SET_NULL,
        related_name="media",
        null=True,
        blank=True,
    )
    media_type = models.CharField(
        max_length=20,
        choices=MediaType.choices,
        default=MediaType.IMAGE,
    )
    file_url = models.TextField()
    thumbnail_url = models.TextField(null=True, blank=True)
    alt_text = models.CharField(max_length=255, null=True, blank=True)
    sort_order = models.SmallIntegerField(default=0)
    is_primary = models.BooleanField(default=False)

    class Meta:
        ordering = ("sort_order", "created_at", "id")
        constraints = [
            models.UniqueConstraint(
                fields=("product",),
                condition=Q(is_primary=True),
                name="product_primary_media_uniq",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.product_id}:{self.media_type}"
