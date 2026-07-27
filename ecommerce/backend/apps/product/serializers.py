from collections import OrderedDict

from django.conf import settings
from rest_framework import serializers

from apps.catalog.models import Brand, Category

from .models import (
    Attribute,
    AttributeValue,
    Product,
    ProductMedia,
    ProductVariant,
)


def _thumbnail_for_product(product: Product) -> str | None:
    images = [
        media for media in product.media.all() if media.media_type == ProductMedia.MediaType.IMAGE
    ]
    primary = next((media for media in images if media.is_primary), None)
    return (primary or (images[0] if images else None)).file_url if images else None


class SellerProductCreateSerializer(serializers.ModelSerializer):
    category_id = serializers.PrimaryKeyRelatedField(
        source="category",
        queryset=Category.objects.filter(is_active=True, is_deleted=False),
    )
    brand_id = serializers.PrimaryKeyRelatedField(
        source="brand",
        queryset=Brand.objects.filter(is_active=True, is_deleted=False),
        allow_null=True,
        required=False,
    )

    class Meta:
        model = Product
        fields = (
            "name",
            "category_id",
            "brand_id",
            "short_description",
            "description",
        )
        extra_kwargs = {
            "short_description": {
                "allow_blank": True,
                "allow_null": True,
                "required": False,
            },
            "description": {
                "allow_blank": True,
                "allow_null": True,
                "required": False,
            },
        }

    def to_internal_value(self, data):
        if "shop_id" in data or "shop" in data:
            raise serializers.ValidationError(
                {"shop_id": ["Gian hàng được xác định từ tài khoản đăng nhập"]}
            )
        return super().to_internal_value(data)


class SellerProductUpdateSerializer(serializers.ModelSerializer):
    category_id = serializers.PrimaryKeyRelatedField(
        source="category",
        queryset=Category.objects.filter(is_active=True, is_deleted=False),
        required=False,
    )
    brand_id = serializers.PrimaryKeyRelatedField(
        source="brand",
        queryset=Brand.objects.filter(is_active=True, is_deleted=False),
        allow_null=True,
        required=False,
    )

    class Meta:
        model = Product
        fields = (
            "name",
            "category_id",
            "brand_id",
            "short_description",
            "description",
        )
        extra_kwargs = {
            "name": {"required": False},
            "short_description": {
                "allow_blank": True,
                "allow_null": True,
                "required": False,
            },
            "description": {
                "allow_blank": True,
                "allow_null": True,
                "required": False,
            },
        }

    def to_internal_value(self, data):
        if "shop_id" in data or "shop" in data:
            raise serializers.ValidationError(
                {"shop_id": ["Gian hàng được xác định từ tài khoản đăng nhập"]}
            )
        return super().to_internal_value(data)

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError("Cần cung cấp ít nhất một trường để cập nhật")
        return attrs


class ProductMediaSerializer(serializers.ModelSerializer):
    variant_id = serializers.UUIDField(allow_null=True, read_only=True)

    class Meta:
        model = ProductMedia
        fields = (
            "id",
            "variant_id",
            "media_type",
            "file_url",
            "thumbnail_url",
            "alt_text",
            "sort_order",
            "is_primary",
            "created_at",
        )
        read_only_fields = fields


class AttributeValueSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttributeValue
        fields = (
            "id",
            "value",
            "display_value",
            "color_code",
            "sort_order",
        )
        read_only_fields = fields


class AttributeListSerializer(serializers.ModelSerializer):
    values = AttributeValueSerializer(many=True, read_only=True)
    scope = serializers.SerializerMethodField()

    class Meta:
        model = Attribute
        fields = (
            "id",
            "name",
            "code",
            "display_type",
            "sort_order",
            "scope",
            "values",
        )
        read_only_fields = fields

    def get_scope(self, attribute: Attribute) -> str:
        return "global" if attribute.shop_id is None else "shop"


class VariantAttributeValueSerializer(serializers.Serializer):
    attribute_id = serializers.UUIDField(source="attribute.id", read_only=True)
    attribute_name = serializers.CharField(source="attribute.name", read_only=True)
    attribute_value_id = serializers.UUIDField(
        source="attribute_value.id",
        read_only=True,
    )
    value = serializers.CharField(source="attribute_value.value", read_only=True)
    display_value = serializers.CharField(
        source="attribute_value.display_value",
        allow_null=True,
        read_only=True,
    )
    color_code = serializers.CharField(
        source="attribute_value.color_code",
        allow_null=True,
        read_only=True,
    )


class SellerProductVariantSerializer(serializers.ModelSerializer):
    attributes = VariantAttributeValueSerializer(
        source="variant_attribute_links",
        many=True,
        read_only=True,
    )

    class Meta:
        model = ProductVariant
        fields = (
            "id",
            "sku",
            "barcode",
            "name",
            "original_price",
            "sale_price",
            "cost_price",
            "weight_grams",
            "is_active",
            "attributes",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class PublicProductVariantSerializer(serializers.ModelSerializer):
    attributes = VariantAttributeValueSerializer(
        source="variant_attribute_links",
        many=True,
        read_only=True,
    )

    class Meta:
        model = ProductVariant
        fields = (
            "id",
            "sku",
            "name",
            "original_price",
            "sale_price",
            "weight_grams",
            "attributes",
        )
        read_only_fields = fields


class CategorySummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("id", "name", "slug")
        read_only_fields = fields


class BrandSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = ("id", "name", "slug", "logo_url")
        read_only_fields = fields


class ProductAttributesMixin:
    def get_attributes(self, product: Product) -> list[dict]:
        grouped: OrderedDict[str, dict] = OrderedDict()
        for link in product.product_attribute_links.all():
            value = link.attribute_value
            attribute = value.attribute
            key = str(attribute.pk)
            if key not in grouped:
                grouped[key] = {
                    "id": key,
                    "name": attribute.name,
                    "code": attribute.code,
                    "display_type": attribute.display_type,
                    "values": [],
                }
            grouped[key]["values"].append(AttributeValueSerializer(value).data)
        return list(grouped.values())


class SellerProductListSerializer(serializers.ModelSerializer):
    thumbnail = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = (
            "id",
            "name",
            "slug",
            "status",
            "thumbnail",
            "min_price",
            "max_price",
            "created_at",
        )
        read_only_fields = fields

    def get_thumbnail(self, product: Product) -> str | None:
        return _thumbnail_for_product(product)


class SellerProductDetailSerializer(
    ProductAttributesMixin,
    serializers.ModelSerializer,
):
    category = CategorySummarySerializer(read_only=True)
    brand = BrandSummarySerializer(read_only=True)
    media = ProductMediaSerializer(many=True, read_only=True)
    variants = SellerProductVariantSerializer(many=True, read_only=True)
    attributes = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = (
            "id",
            "name",
            "slug",
            "short_description",
            "description",
            "status",
            "rejection_reason",
            "category",
            "brand",
            "media",
            "variants",
            "attributes",
            "min_price",
            "max_price",
            "rating_average",
            "rating_count",
            "sold_count",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class AdminProductListSerializer(serializers.ModelSerializer):
    shop_name = serializers.CharField(source="shop.name", read_only=True)
    seller_id = serializers.IntegerField(source="shop.owner.id", read_only=True)
    seller_email = serializers.EmailField(source="shop.owner.email", read_only=True)
    seller_name = serializers.CharField(source="shop.owner.full_name", read_only=True)
    category = CategorySummarySerializer(read_only=True)
    thumbnail = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = (
            "id",
            "name",
            "slug",
            "status",
            "rejection_reason",
            "thumbnail",
            "min_price",
            "max_price",
            "category",
            "shop_name",
            "seller_id",
            "seller_email",
            "seller_name",
            "created_at",
        )
        read_only_fields = fields

    def get_thumbnail(self, product: Product) -> str | None:
        return _thumbnail_for_product(product)


class AdminProductRejectSerializer(serializers.Serializer):
    rejection_reason = serializers.CharField(
        max_length=2000,
        allow_blank=False,
        trim_whitespace=True,
    )


class PublicProductListSerializer(serializers.ModelSerializer):
    thumbnail = serializers.SerializerMethodField()
    shop_name = serializers.CharField(source="shop.name", read_only=True)
    shop_slug = serializers.SlugField(source="shop.slug", read_only=True)

    class Meta:
        model = Product
        fields = (
            "id",
            "name",
            "slug",
            "thumbnail",
            "min_price",
            "max_price",
            "rating_average",
            "rating_count",
            "sold_count",
            "shop_name",
            "shop_slug",
        )
        read_only_fields = fields

    def get_thumbnail(self, product: Product) -> str | None:
        return _thumbnail_for_product(product)


class PublicShopSummarySerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(read_only=True)
    slug = serializers.SlugField(read_only=True)
    logo_url = serializers.SerializerMethodField()
    average_rating = serializers.DecimalField(
        max_digits=3,
        decimal_places=2,
        read_only=True,
    )

    def get_logo_url(self, shop) -> str:
        if shop.logo:
            request = self.context.get("request")
            return request.build_absolute_uri(shop.logo.url) if request else shop.logo.url
        return shop.logo_url


class PublicProductDetailSerializer(
    ProductAttributesMixin,
    serializers.ModelSerializer,
):
    category = CategorySummarySerializer(read_only=True)
    brand = BrandSummarySerializer(read_only=True)
    shop = PublicShopSummarySerializer(read_only=True)
    media = ProductMediaSerializer(many=True, read_only=True)
    variants = PublicProductVariantSerializer(many=True, read_only=True)
    attributes = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = (
            "id",
            "name",
            "slug",
            "short_description",
            "description",
            "category",
            "brand",
            "shop",
            "media",
            "variants",
            "attributes",
            "min_price",
            "max_price",
            "rating_average",
            "rating_count",
            "sold_count",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class MediaUploadSerializer(serializers.Serializer):
    file = serializers.FileField()
    media_type = serializers.ChoiceField(choices=ProductMedia.MediaType.choices)

    def validate(self, attrs):
        uploaded_file = attrs["file"]
        media_type = attrs["media_type"]
        is_image = media_type == ProductMedia.MediaType.IMAGE
        max_mb = settings.MAX_IMAGE_UPLOAD_MB if is_image else settings.MAX_VIDEO_UPLOAD_MB
        if uploaded_file.size <= 0 or uploaded_file.size > max_mb * 1024 * 1024:
            raise serializers.ValidationError(
                {"file": [f"Tệp phải lớn hơn 0 byte và không quá {max_mb} MB"]}
            )
        allowed_content_types = (
            {"image/jpeg", "image/png", "image/webp"}
            if is_image
            else {"video/mp4", "video/webm", "application/octet-stream"}
        )
        if uploaded_file.content_type not in allowed_content_types:
            raise serializers.ValidationError(
                {"file": ["Content-Type của media không được hỗ trợ"]}
            )
        return attrs


class MediaReorderSerializer(serializers.Serializer):
    ordered_ids = serializers.ListField(
        child=serializers.UUIDField(),
        allow_empty=True,
    )

    def validate_ordered_ids(self, ordered_ids):
        if len(ordered_ids) != len(set(ordered_ids)):
            raise serializers.ValidationError("Mỗi media chỉ được xuất hiện một lần")
        return ordered_ids


class VariantGenerateSerializer(serializers.Serializer):
    attribute_value_ids = serializers.ListField(
        child=serializers.UUIDField(),
        allow_empty=False,
    )

    def validate_attribute_value_ids(self, value_ids):
        if len(value_ids) != len(set(value_ids)):
            raise serializers.ValidationError("Mỗi giá trị thuộc tính chỉ được xuất hiện một lần")
        return value_ids


class VariantUpdateSerializer(serializers.ModelSerializer):
    original_price = serializers.DecimalField(
        max_digits=18,
        decimal_places=0,
        min_value=0,
        required=False,
    )
    sale_price = serializers.DecimalField(
        max_digits=18,
        decimal_places=0,
        min_value=0,
        required=False,
    )
    cost_price = serializers.DecimalField(
        max_digits=18,
        decimal_places=0,
        min_value=0,
        allow_null=True,
        required=False,
    )
    weight_grams = serializers.IntegerField(min_value=1, required=False)

    class Meta:
        model = ProductVariant
        fields = (
            "sku",
            "barcode",
            "original_price",
            "sale_price",
            "cost_price",
            "weight_grams",
            "is_active",
        )
        extra_kwargs = {
            "sku": {"required": False, "allow_blank": True},
            "barcode": {"required": False, "allow_blank": True, "allow_null": True},
            "is_active": {"required": False},
        }

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError("Cần cung cấp ít nhất một trường để cập nhật")
        instance = self.instance
        original_price = attrs.get(
            "original_price",
            instance.original_price if instance else None,
        )
        sale_price = attrs.get(
            "sale_price",
            instance.sale_price if instance else None,
        )
        if (
            original_price is not None
            and sale_price is not None
            and original_price != 0
            and sale_price > original_price
        ):
            raise serializers.ValidationError(
                {"sale_price": ["Giá bán phải nhỏ hơn hoặc bằng giá gốc"]}
            )
        return attrs


PRODUCT_SORT_CHOICES = (
    "created_at",
    "-created_at",
    "price",
    "-price",
    "sold_count",
    "-sold_count",
    "rating",
    "-rating",
)


class SellerProductFilterSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Product.Status.choices, required=False)
    category_id = serializers.UUIDField(required=False)
    search = serializers.CharField(
        max_length=255,
        trim_whitespace=True,
        required=False,
    )
    sort = serializers.ChoiceField(
        choices=PRODUCT_SORT_CHOICES,
        default="-created_at",
    )


class PublicProductFilterSerializer(serializers.Serializer):
    category_id = serializers.UUIDField(required=False)
    brand_id = serializers.UUIDField(required=False)
    min_price = serializers.DecimalField(
        max_digits=18,
        decimal_places=0,
        min_value=0,
        required=False,
    )
    max_price = serializers.DecimalField(
        max_digits=18,
        decimal_places=0,
        min_value=0,
        required=False,
    )
    search = serializers.CharField(
        max_length=255,
        trim_whitespace=True,
        required=False,
    )
    sort = serializers.ChoiceField(
        choices=PRODUCT_SORT_CHOICES,
        default="-created_at",
    )

    def validate(self, attrs):
        min_price = attrs.get("min_price")
        max_price = attrs.get("max_price")
        if min_price is not None and max_price is not None and min_price > max_price:
            raise serializers.ValidationError(
                {"max_price": ["Giá tối đa phải lớn hơn hoặc bằng giá tối thiểu"]}
            )
        return attrs


class ProductPaginationMetaSerializer(serializers.Serializer):
    page = serializers.IntegerField()
    page_size = serializers.IntegerField()
    total_items = serializers.IntegerField()
    total_pages = serializers.IntegerField()


class SellerProductResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    data = SellerProductDetailSerializer()


class SellerProductListResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    data = SellerProductListSerializer(many=True)
    meta = ProductPaginationMetaSerializer()


class AdminProductListResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    data = AdminProductListSerializer(many=True)
    meta = ProductPaginationMetaSerializer()


class AdminProductResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    data = AdminProductListSerializer()


class PublicProductListResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    data = PublicProductListSerializer(many=True)
    meta = ProductPaginationMetaSerializer()


class PublicProductResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    data = PublicProductDetailSerializer()


class MediaResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    data = ProductMediaSerializer()


class VariantResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    data = SellerProductVariantSerializer()


class VariantListResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    data = SellerProductVariantSerializer(many=True)


class AttributeListResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    data = AttributeListSerializer(many=True)
    meta = ProductPaginationMetaSerializer()


class ProductDeleteResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    data = serializers.DictField()
