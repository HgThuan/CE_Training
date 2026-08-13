from rest_framework import serializers


class CartItemAddSerializer(serializers.Serializer):
    variant_id = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1, default=1)
    is_selected = serializers.BooleanField(default=True)


class CartItemUpdateSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=1, required=False)
    is_selected = serializers.BooleanField(required=False)

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError("Cần ít nhất một trường để cập nhật")
        return attrs


class GuestCartItemSerializer(serializers.Serializer):
    variant_id = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1)


class CartMergeSerializer(serializers.Serializer):
    items = GuestCartItemSerializer(many=True)


class CartPreviewSerializer(serializers.Serializer):
    selected_item_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
    )
    voucher_codes = serializers.DictField(required=False, default=dict)
