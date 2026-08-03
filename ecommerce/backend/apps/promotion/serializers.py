from rest_framework import serializers

from apps.product.models import ProductVariant
from apps.promotion.models import FlashSale, FlashSaleItem, UserVoucher, Voucher


class VoucherSerializer(serializers.ModelSerializer):
    shop_name = serializers.CharField(source="shop.name", read_only=True)
    category_name = serializers.CharField(source="applicable_category.name", read_only=True)
    is_valid_now = serializers.BooleanField(read_only=True)
    issuer_type = serializers.CharField(source="scope", read_only=True)
    issuer_id = serializers.IntegerField(source="shop_id", read_only=True)
    value = serializers.DecimalField(
        source="discount_value",
        max_digits=18,
        decimal_places=0,
        read_only=True,
    )
    min_order_value = serializers.DecimalField(
        source="min_order_amount",
        max_digits=18,
        decimal_places=0,
        read_only=True,
    )
    total_quantity = serializers.IntegerField(source="total_usage_limit", read_only=True)
    per_user_limit = serializers.IntegerField(source="usage_limit_per_user", read_only=True)
    start_time = serializers.DateTimeField(source="valid_from", read_only=True)
    end_time = serializers.DateTimeField(source="valid_until", read_only=True)
    issued_quantity = serializers.IntegerField(read_only=True)

    class Meta:
        model = Voucher
        fields = (
            "id",
            "issuer_type",
            "issuer_id",
            "scope",
            "shop",
            "shop_name",
            "code",
            "name",
            "description",
            "discount_type",
            "discount_value",
            "value",
            "max_discount_amount",
            "min_order_amount",
            "min_order_value",
            "total_usage_limit",
            "total_quantity",
            "remaining_quantity",
            "usage_limit_per_user",
            "per_user_limit",
            "valid_from",
            "start_time",
            "valid_until",
            "end_time",
            "collect_type",
            "stackable_with",
            "applicable_scope",
            "applicable_category",
            "category_name",
            "is_active",
            "is_valid_now",
            "issued_quantity",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("created_at", "updated_at")

    def validate_code(self, value: str) -> str:
        return value.strip().upper()

    def to_internal_value(self, data):
        normalized = data.copy()
        legacy_types = {"percentage": "percent", "fixed_amount": "fixed"}
        discount_type = normalized.get("discount_type")
        if discount_type in legacy_types:
            normalized["discount_type"] = legacy_types[discount_type]
        return super().to_internal_value(normalized)

    def validate(self, attrs):
        instance = self.instance
        scope = attrs.get("scope", getattr(instance, "scope", None))
        shop = attrs.get("shop", getattr(instance, "shop", None))
        discount_type = attrs.get(
            "discount_type",
            getattr(instance, "discount_type", None),
        )
        max_discount = attrs.get(
            "max_discount_amount",
            getattr(instance, "max_discount_amount", None),
        )
        valid_from = attrs.get("valid_from", getattr(instance, "valid_from", None))
        valid_until = attrs.get("valid_until", getattr(instance, "valid_until", None))
        total_quantity = attrs.get(
            "total_usage_limit", getattr(instance, "total_usage_limit", None)
        )
        remaining_quantity = attrs.get(
            "remaining_quantity", getattr(instance, "remaining_quantity", None)
        )
        stackable_with = attrs.get("stackable_with", getattr(instance, "stackable_with", []))
        if scope == Voucher.Scope.PLATFORM and shop is not None:
            raise serializers.ValidationError({"shop": "Voucher sàn không thuộc shop"})
        if scope == Voucher.Scope.SHOP and shop is None:
            raise serializers.ValidationError({"shop": "Voucher shop bắt buộc có shop"})
        if discount_type == Voucher.DiscountType.FIXED_AMOUNT and max_discount is not None:
            raise serializers.ValidationError(
                {"max_discount_amount": "Chỉ dùng cho voucher phần trăm"}
            )
        if valid_from and valid_until and valid_from >= valid_until:
            raise serializers.ValidationError({"valid_until": "Phải sau thời điểm bắt đầu"})
        if (
            total_quantity is not None
            and remaining_quantity is not None
            and remaining_quantity > total_quantity
        ):
            raise serializers.ValidationError(
                {"remaining_quantity": "Số lượng còn lại không được vượt tổng phát hành"}
            )
        invalid_stack_types = set(stackable_with) - set(Voucher.Scope.values)
        if invalid_stack_types:
            raise serializers.ValidationError(
                {"stackable_with": "Chỉ chấp nhận platform hoặc shop"}
            )
        return attrs

    def create(self, validated_data):
        if "remaining_quantity" not in validated_data:
            validated_data["remaining_quantity"] = validated_data.get("total_usage_limit")
        return super().create(validated_data)


class UserVoucherSerializer(serializers.ModelSerializer):
    campaign = VoucherSerializer(source="voucher_campaign", read_only=True)

    class Meta:
        model = UserVoucher
        fields = (
            "id",
            "campaign",
            "status",
            "claimed_at",
            "used_at",
            "order_id",
            "checkout_token",
            "pending_expires_at",
        )


class VoucherCenterSerializer(VoucherSerializer):
    is_collected = serializers.SerializerMethodField()

    class Meta(VoucherSerializer.Meta):
        fields = (*VoucherSerializer.Meta.fields, "is_collected")

    def get_is_collected(self, obj: Voucher) -> bool:
        customer = self.context.get("customer")
        if customer is None:
            return False
        claimed_count = getattr(obj, "claimed_count", None)
        if claimed_count is not None:
            return claimed_count >= obj.usage_limit_per_user
        return obj.user_vouchers.filter(user=customer).count() >= obj.usage_limit_per_user


class VoucherCollectSerializer(serializers.Serializer):
    idempotency_key = serializers.CharField(max_length=128, required=False, allow_blank=True)


class CheckoutVoucherApplySerializer(serializers.Serializer):
    user_voucher_ids = serializers.ListField(
        child=serializers.UUIDField(),
        allow_empty=True,
    )
    checkout_token = serializers.UUIDField(required=False)
    selected_item_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
    )


class CheckoutVoucherCodeSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=50)
    idempotency_key = serializers.CharField(max_length=128)
    checkout_token = serializers.UUIDField(required=False)
    selected_item_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
    )


class FlashSaleItemSerializer(serializers.ModelSerializer):
    product_id = serializers.UUIDField(source="variant.product_id", read_only=True)
    product_name = serializers.CharField(source="variant.product.name", read_only=True)
    product_slug = serializers.CharField(source="variant.product.slug", read_only=True)
    variant_sku = serializers.CharField(source="variant.sku", read_only=True)
    shop_id = serializers.IntegerField(source="variant.shop_id", read_only=True)
    shop_name = serializers.CharField(source="variant.shop.name", read_only=True)
    original_price = serializers.DecimalField(
        source="variant.sale_price",
        max_digits=18,
        decimal_places=0,
        read_only=True,
    )
    remaining_quota = serializers.IntegerField(read_only=True)
    primary_image = serializers.SerializerMethodField()

    class Meta:
        model = FlashSaleItem
        fields = (
            "id",
            "variant",
            "product_id",
            "product_name",
            "product_slug",
            "variant_sku",
            "shop_id",
            "shop_name",
            "primary_image",
            "original_price",
            "sale_price",
            "quota",
            "sold_count",
            "remaining_quota",
        )
        read_only_fields = ("sold_count",)

    def get_primary_image(self, obj: FlashSaleItem) -> str | None:
        media = list(obj.variant.product.media.all())
        primary = next((entry for entry in media if entry.is_primary), media[0] if media else None)
        return primary.file_url if primary else None

    def validate(self, attrs):
        variant = attrs.get("variant", getattr(self.instance, "variant", None))
        sale_price = attrs.get("sale_price", getattr(self.instance, "sale_price", None))
        quota = attrs.get("quota", getattr(self.instance, "quota", None))
        sold_count = getattr(self.instance, "sold_count", 0)
        if variant and sale_price is not None and sale_price > variant.sale_price:
            raise serializers.ValidationError({"sale_price": "Giá sale không được cao hơn giá bán"})
        if quota is not None and quota < sold_count:
            raise serializers.ValidationError({"quota": "Quota không được thấp hơn số đã bán"})
        return attrs


class FlashSaleCatalogVariantSerializer(serializers.ModelSerializer):
    product_id = serializers.UUIDField(source="product.id", read_only=True)
    product_name = serializers.CharField(source="product.name", read_only=True)
    category_id = serializers.UUIDField(source="product.category_id", read_only=True)
    category_name = serializers.CharField(source="product.category.name", read_only=True)
    shop_id = serializers.IntegerField(source="shop.id", read_only=True)
    shop_name = serializers.CharField(source="shop.name", read_only=True)
    available_stock = serializers.IntegerField(read_only=True)
    primary_image = serializers.SerializerMethodField()

    class Meta:
        model = ProductVariant
        fields = (
            "id",
            "sku",
            "name",
            "sale_price",
            "available_stock",
            "product_id",
            "product_name",
            "category_id",
            "category_name",
            "shop_id",
            "shop_name",
            "primary_image",
        )

    def get_primary_image(self, obj: ProductVariant) -> str | None:
        media = list(obj.product.media.all())
        primary = next((entry for entry in media if entry.is_primary), media[0] if media else None)
        return primary.file_url if primary else None


class FlashSaleSerializer(serializers.ModelSerializer):
    items = FlashSaleItemSerializer(many=True, required=False)
    status = serializers.CharField(read_only=True)

    class Meta:
        model = FlashSale
        fields = (
            "id",
            "name",
            "start_time",
            "end_time",
            "is_active",
            "status",
            "items",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("created_at", "updated_at")

    def validate(self, attrs):
        start = attrs.get("start_time", getattr(self.instance, "start_time", None))
        end = attrs.get("end_time", getattr(self.instance, "end_time", None))
        if start and end and start >= end:
            raise serializers.ValidationError({"end_time": "Phải sau thời điểm bắt đầu"})
        return attrs

    def create(self, validated_data):
        items = validated_data.pop("items", [])
        flash_sale = FlashSale.objects.create(**validated_data)
        FlashSaleItem.objects.bulk_create(
            [FlashSaleItem(flash_sale=flash_sale, **item) for item in items]
        )
        return flash_sale

    def update(self, instance, validated_data):
        items = validated_data.pop("items", None)
        instance = super().update(instance, validated_data)
        if items is not None:
            seen = set()
            for item_data in items:
                variant = item_data["variant"]
                seen.add(variant.id)
                FlashSaleItem.objects.update_or_create(
                    flash_sale=instance,
                    variant=variant,
                    defaults={
                        "sale_price": item_data["sale_price"],
                        "quota": item_data["quota"],
                    },
                )
            instance.items.exclude(variant_id__in=seen).filter(sold_count=0).delete()
        return instance
