from rest_framework import serializers

from apps.promotion.models import FlashSale, FlashSaleItem, Voucher


class VoucherSerializer(serializers.ModelSerializer):
    shop_name = serializers.CharField(source="shop.name", read_only=True)
    category_name = serializers.CharField(source="applicable_category.name", read_only=True)
    is_valid_now = serializers.BooleanField(read_only=True)

    class Meta:
        model = Voucher
        fields = (
            "id",
            "scope",
            "shop",
            "shop_name",
            "code",
            "name",
            "description",
            "discount_type",
            "discount_value",
            "max_discount_amount",
            "min_order_amount",
            "total_usage_limit",
            "usage_limit_per_user",
            "valid_from",
            "valid_until",
            "applicable_category",
            "category_name",
            "is_active",
            "is_valid_now",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("created_at", "updated_at")

    def validate_code(self, value: str) -> str:
        return value.strip().upper()

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
        return attrs


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
