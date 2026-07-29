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
    images = getattr(product, "_public_list_images", None)
    if images is None:
        images = [
            media
            for media in product.media.all()
            if media.media_type == ProductMedia.MediaType.IMAGE
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


class AttributeValueCreateSerializer(serializers.Serializer):
    value = serializers.CharField(max_length=120, trim_whitespace=True)
    display_value = serializers.CharField(
        max_length=120,
        trim_whitespace=True,
        allow_blank=True,
        required=False,
    )
    color_code = serializers.RegexField(
        regex=r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$",
        max_length=9,
        allow_blank=True,
        required=False,
        error_messages={"invalid": "Mã màu phải có dạng #RGB, #RRGGBB hoặc #RRGGBBAA"},
    )


class AttributeCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100, trim_whitespace=True)
    code = serializers.SlugField(
        max_length=100,
        allow_blank=True,
        required=False,
    )
    display_type = serializers.ChoiceField(
        choices=Attribute.DisplayType.choices,
        default=Attribute.DisplayType.TEXT,
    )
    values = AttributeValueCreateSerializer(many=True, allow_empty=False)

    def validate_values(self, values):
        normalized_values = [item["value"].casefold() for item in values]
        if len(normalized_values) != len(set(normalized_values)):
            raise serializers.ValidationError("Mỗi giá trị chỉ được xuất hiện một lần")
        return values


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
    # stock_quantity remains a read-only compatibility alias during the Sprint 4 migration.
    stock_quantity = serializers.IntegerField(source="available_stock", read_only=True)
    available_stock = serializers.IntegerField(read_only=True)
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
            "stock_quantity",
            "available_stock",
            "weight_grams",
            "is_active",
            "attributes",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class PublicProductVariantSerializer(serializers.ModelSerializer):
    stock_quantity = serializers.IntegerField(source="available_stock", read_only=True)
    available_stock = serializers.IntegerField(read_only=True)
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
            "stock_quantity",
            "available_stock",
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


class SearchSuggestionSerializer(serializers.ModelSerializer):
    text = serializers.CharField(source="name", read_only=True)
    shop_slug = serializers.SlugField(source="shop.slug", read_only=True)

    class Meta:
        model = Product
        fields = (
            "id",
            "text",
            "slug",
            "shop_slug",
        )
        read_only_fields = fields


class PublicShopSummarySerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(read_only=True)
    slug = serializers.SlugField(read_only=True)
    logo_url = serializers.URLField(read_only=True)
    average_rating = serializers.DecimalField(
        max_digits=3,
        decimal_places=2,
        read_only=True,
    )


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
    variant_id = serializers.UUIDField(allow_null=True, required=False)

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
        if attrs.get("variant_id") is not None and not is_image:
            raise serializers.ValidationError(
                {"variant_id": ["Media riêng của biến thể phải là ảnh"]}
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


class VariantLookupSerializer(serializers.Serializer):
    barcode = serializers.CharField(max_length=100, trim_whitespace=True)


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
    stock_quantity = serializers.IntegerField(source="available_stock", read_only=True)
    available_stock = serializers.IntegerField(read_only=True)
    weight_grams = serializers.IntegerField(min_value=1, required=False)

    class Meta:
        model = ProductVariant
        fields = (
            "sku",
            "barcode",
            "original_price",
            "sale_price",
            "cost_price",
            "stock_quantity",
            "available_stock",
            "weight_grams",
            "is_active",
        )
        extra_kwargs = {
            "sku": {"required": False, "allow_blank": True},
            "barcode": {"required": False, "allow_blank": True, "allow_null": True},
            "is_active": {"required": False},
        }

    def to_internal_value(self, data):
        if "stock_quantity" in data or "available_stock" in data:
            raise serializers.ValidationError(
                {
                    "stock_quantity": [
                        "Tồn kho chỉ được thay đổi qua phiếu nhập/xuất trong module Kho"
                    ]
                }
            )
        return super().to_internal_value(data)

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
    "avg_rating",
    "-avg_rating",
)
SEARCH_SORT_CHOICES = (*PRODUCT_SORT_CHOICES, "relevance")
FILTER_ALIASES = {
    "category_id": "category",
    "brand_id": "brand",
    "min_price": "price_min",
    "max_price": "price_max",
    "search": "q",
}
SORT_ALIASES = {
    "rating": "avg_rating",
    "-rating": "-avg_rating",
}


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
    category = serializers.CharField(max_length=180, required=False)
    brand = serializers.CharField(max_length=180, required=False)
    price_min = serializers.DecimalField(
        max_digits=18,
        decimal_places=0,
        min_value=0,
        required=False,
    )
    price_max = serializers.DecimalField(
        max_digits=18,
        decimal_places=0,
        min_value=0,
        required=False,
    )
    rating_min = serializers.DecimalField(
        max_digits=3,
        decimal_places=2,
        min_value=0,
        max_value=5,
        required=False,
    )
    in_stock = serializers.BooleanField(required=False)
    shop = serializers.CharField(max_length=255, required=False)
    q = serializers.CharField(
        max_length=255,
        trim_whitespace=True,
        allow_blank=True,
        required=False,
    )

    # Sprint 3 compatibility aliases. Validation normalizes these into the
    # canonical Sprint 5 names before selectors receive the data.
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
        allow_blank=True,
        required=False,
    )
    sort = serializers.ChoiceField(
        choices=PRODUCT_SORT_CHOICES,
        required=False,
    )
    page = serializers.IntegerField(min_value=1, required=False)
    page_size = serializers.IntegerField(min_value=1, max_value=100, required=False)

    def to_internal_value(self, data):
        unknown = sorted(set(data.keys()) - set(self.fields))
        if unknown:
            raise serializers.ValidationError(
                {"query_params": [f"Tham số không được hỗ trợ: {', '.join(unknown)}"]}
            )
        return super().to_internal_value(data)

    def validate(self, attrs):
        attrs = dict(attrs)
        legacy_price_range = "min_price" in attrs or "max_price" in attrs
        for alias, canonical in FILTER_ALIASES.items():
            if alias not in attrs:
                continue
            alias_value = attrs.pop(alias)
            if canonical in attrs and str(attrs[canonical]) != str(alias_value):
                raise serializers.ValidationError(
                    {canonical: [f"Không thể dùng đồng thời {canonical} và {alias}"]}
                )
            if canonical not in attrs:
                attrs[canonical] = (
                    str(alias_value) if canonical in {"category", "brand", "q"} else alias_value
                )

        if sort := attrs.get("sort"):
            attrs["sort"] = SORT_ALIASES.get(sort, sort)

        price_min = attrs.get("price_min")
        price_max = attrs.get("price_max")
        if price_min is not None and price_max is not None and price_min > price_max:
            raise serializers.ValidationError(
                {
                    "max_price" if legacy_price_range else "price_max": [
                        "Giá tối đa phải lớn hơn hoặc bằng giá tối thiểu"
                    ]
                }
            )
        return attrs


class SearchFilterSerializer(PublicProductFilterSerializer):
    sort = serializers.ChoiceField(
        choices=SEARCH_SORT_CHOICES,
        required=False,
    )

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if attrs.get("sort") == "relevance" and not attrs.get("q"):
            raise serializers.ValidationError(
                {"sort": ["Sắp xếp relevance yêu cầu query q không rỗng"]}
            )
        return attrs


class SearchSuggestionQuerySerializer(serializers.Serializer):
    q = serializers.CharField(
        min_length=1,
        max_length=100,
        trim_whitespace=True,
    )
    limit = serializers.IntegerField(min_value=1, max_value=10, default=10)

    def to_internal_value(self, data):
        unknown = sorted(set(data.keys()) - set(self.fields))
        if unknown:
            raise serializers.ValidationError(
                {"query_params": [f"Tham số không được hỗ trợ: {', '.join(unknown)}"]}
            )
        return super().to_internal_value(data)


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


class SearchSuggestionListResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    data = SearchSuggestionSerializer(many=True)


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


class AttributeResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    data = AttributeListSerializer()


class ProductDeleteResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    data = serializers.DictField()
