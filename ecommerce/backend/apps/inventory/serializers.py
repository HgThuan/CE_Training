from rest_framework import serializers

from .models import (
    InventoryBalance,
    StockAlert,
    StockEntry,
    StockEntryItem,
    StockMovement,
    StockOutEntry,
    StockOutEntryItem,
)


class InventoryBalanceSerializer(serializers.ModelSerializer):
    variant_id = serializers.UUIDField(source="variant.id", read_only=True)
    sku = serializers.CharField(source="variant.sku", read_only=True)
    variant_name = serializers.CharField(source="variant.name", read_only=True)
    product_id = serializers.UUIDField(source="variant.product.id", read_only=True)
    product_name = serializers.CharField(source="variant.product.name", read_only=True)
    is_low_stock = serializers.SerializerMethodField()

    class Meta:
        model = InventoryBalance
        fields = (
            "variant_id",
            "product_id",
            "product_name",
            "sku",
            "variant_name",
            "available_stock",
            "reserved_stock",
            "low_stock_threshold",
            "is_low_stock",
            "updated_at",
        )
        read_only_fields = fields

    def get_is_low_stock(self, balance: InventoryBalance) -> bool:
        return balance.available_stock <= balance.low_stock_threshold


class StockMovementSerializer(serializers.ModelSerializer):
    variant_id = serializers.UUIDField(source="variant.id", read_only=True)
    sku = serializers.CharField(source="variant.sku", read_only=True)
    product_name = serializers.CharField(source="variant.product.name", read_only=True)
    created_by = serializers.CharField(source="created_by.email", read_only=True)

    class Meta:
        model = StockMovement
        fields = (
            "id",
            "variant_id",
            "product_name",
            "sku",
            "movement_type",
            "bucket",
            "quantity",
            "balance_after",
            "reference_type",
            "reference_id",
            "note",
            "created_by",
            "created_at",
        )
        read_only_fields = fields


class StockEntryItemWriteSerializer(serializers.Serializer):
    variant_id = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1)
    unit_cost = serializers.DecimalField(
        max_digits=18,
        decimal_places=0,
        min_value=0,
    )


class StockEntryWriteSerializer(serializers.Serializer):
    supplier_name = serializers.CharField(max_length=255, trim_whitespace=True)
    note = serializers.CharField(allow_blank=True, required=False)
    items = StockEntryItemWriteSerializer(many=True, allow_empty=False)

    def to_internal_value(self, data):
        if "shop" in data or "shop_id" in data or "status" in data:
            raise serializers.ValidationError(
                {"shop_id": ["Gian hàng và trạng thái do hệ thống xác định"]}
            )
        return super().to_internal_value(data)


class StockEntryUpdateSerializer(serializers.Serializer):
    supplier_name = serializers.CharField(
        max_length=255,
        trim_whitespace=True,
        required=False,
    )
    note = serializers.CharField(allow_blank=True, required=False)
    items = StockEntryItemWriteSerializer(many=True, allow_empty=False, required=False)

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError("Cần cung cấp ít nhất một trường để cập nhật")
        return attrs


class StockEntryItemSerializer(serializers.ModelSerializer):
    variant_id = serializers.UUIDField(source="variant.id", read_only=True)
    sku = serializers.CharField(source="variant.sku", read_only=True)
    product_name = serializers.CharField(source="variant.product.name", read_only=True)

    class Meta:
        model = StockEntryItem
        fields = (
            "id",
            "variant_id",
            "product_name",
            "sku",
            "quantity",
            "unit_cost",
        )
        read_only_fields = fields


class StockEntrySerializer(serializers.ModelSerializer):
    items = StockEntryItemSerializer(many=True, read_only=True)
    created_by = serializers.CharField(source="created_by.email", read_only=True)
    confirmed_by = serializers.CharField(
        source="confirmed_by.email",
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = StockEntry
        fields = (
            "id",
            "supplier_name",
            "status",
            "note",
            "items",
            "created_by",
            "confirmed_by",
            "confirmed_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class StockOutEntryItemWriteSerializer(serializers.Serializer):
    variant_id = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=0)


class StockOutEntryWriteSerializer(serializers.Serializer):
    entry_type = serializers.ChoiceField(choices=StockOutEntry.EntryType.choices)
    reason = serializers.CharField(trim_whitespace=True, allow_blank=False)
    items = StockOutEntryItemWriteSerializer(many=True, allow_empty=False)

    def validate(self, attrs):
        if attrs.get("entry_type") == StockOutEntry.EntryType.OUT and any(
            item["quantity"] <= 0 for item in attrs.get("items", [])
        ):
            raise serializers.ValidationError({"items": ["Số lượng của phiếu xuất phải lớn hơn 0"]})
        return attrs

    def to_internal_value(self, data):
        if "shop" in data or "shop_id" in data or "status" in data:
            raise serializers.ValidationError(
                {"shop_id": ["Gian hàng và trạng thái do hệ thống xác định"]}
            )
        return super().to_internal_value(data)


class StockOutEntryUpdateSerializer(StockOutEntryWriteSerializer):
    entry_type = serializers.ChoiceField(
        choices=StockOutEntry.EntryType.choices,
        required=False,
    )
    reason = serializers.CharField(
        trim_whitespace=True,
        allow_blank=False,
        required=False,
    )
    items = StockOutEntryItemWriteSerializer(
        many=True,
        allow_empty=False,
        required=False,
    )

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError("Cần cung cấp ít nhất một trường để cập nhật")
        instance = self.context.get("entry")
        entry_type = attrs.get("entry_type", getattr(instance, "entry_type", None))
        if entry_type == StockOutEntry.EntryType.OUT and any(
            item["quantity"] <= 0 for item in attrs.get("items", [])
        ):
            raise serializers.ValidationError({"items": ["Số lượng của phiếu xuất phải lớn hơn 0"]})
        return attrs


class StockOutEntryItemSerializer(serializers.ModelSerializer):
    variant_id = serializers.UUIDField(source="variant.id", read_only=True)
    sku = serializers.CharField(source="variant.sku", read_only=True)
    product_name = serializers.CharField(source="variant.product.name", read_only=True)

    class Meta:
        model = StockOutEntryItem
        fields = ("id", "variant_id", "product_name", "sku", "quantity")
        read_only_fields = fields


class StockOutEntrySerializer(serializers.ModelSerializer):
    items = StockOutEntryItemSerializer(many=True, read_only=True)
    created_by = serializers.CharField(source="created_by.email", read_only=True)
    confirmed_by = serializers.CharField(
        source="confirmed_by.email",
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = StockOutEntry
        fields = (
            "id",
            "entry_type",
            "reason",
            "status",
            "items",
            "created_by",
            "confirmed_by",
            "confirmed_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class ThresholdSerializer(serializers.Serializer):
    low_stock_threshold = serializers.IntegerField(min_value=0)


class MovementFilterSerializer(serializers.Serializer):
    variant_id = serializers.UUIDField(required=False)
    date_from = serializers.DateTimeField(required=False)
    date_to = serializers.DateTimeField(required=False)

    def validate(self, attrs):
        if (
            attrs.get("date_from")
            and attrs.get("date_to")
            and attrs["date_from"] > attrs["date_to"]
        ):
            raise serializers.ValidationError(
                {"date_to": ["Thời điểm kết thúc phải sau thời điểm bắt đầu"]}
            )
        return attrs


class StockAlertSerializer(serializers.ModelSerializer):
    variant_id = serializers.UUIDField(source="variant.id", read_only=True)

    class Meta:
        model = StockAlert
        fields = ("id", "variant_id", "is_notified", "created_at", "updated_at")
        read_only_fields = fields


class InventoryPaginationMetaSerializer(serializers.Serializer):
    page = serializers.IntegerField()
    page_size = serializers.IntegerField()
    total_items = serializers.IntegerField()
    total_pages = serializers.IntegerField()


class InventoryListResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    data = InventoryBalanceSerializer(many=True)
    meta = InventoryPaginationMetaSerializer()


class StockMovementListResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    data = StockMovementSerializer(many=True)
    meta = InventoryPaginationMetaSerializer()


class StockEntryListResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    data = StockEntrySerializer(many=True)
    meta = InventoryPaginationMetaSerializer()


class StockEntryResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    data = StockEntrySerializer()


class StockOutEntryListResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    data = StockOutEntrySerializer(many=True)
    meta = InventoryPaginationMetaSerializer()


class StockOutEntryResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    data = StockOutEntrySerializer()


class InventoryBalanceResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    data = InventoryBalanceSerializer()


class StockAlertResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    data = StockAlertSerializer()
