from rest_framework import serializers

from .models import Dispute, DisputeEvidence, ReturnRequest, ReturnRequestItem, ReturnRequestMedia


class ReturnItemInputSerializer(serializers.Serializer):
    order_item_id = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1)


class ReturnMediaInputSerializer(serializers.Serializer):
    media_type = serializers.ChoiceField(choices=ReturnRequestMedia.MediaType.choices)
    file_url = serializers.URLField(max_length=1000)


class ReturnRequestCreateSerializer(serializers.Serializer):
    shop_order_id = serializers.UUIDField()
    reason_code = serializers.CharField(min_length=1, max_length=50)
    reason_detail = serializers.CharField(min_length=1, max_length=5000)
    items = ReturnItemInputSerializer(many=True, allow_empty=False)
    media = ReturnMediaInputSerializer(many=True, required=False)

    def validate_media(self, value):
        if len(value) > 6:
            raise serializers.ValidationError("Tối đa 6 tệp chứng cứ")
        return value


class ReturnRequestItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="order_item.product_name", read_only=True)
    variant_name = serializers.CharField(source="order_item.variant_name", read_only=True)

    class Meta:
        model = ReturnRequestItem
        fields = (
            "id",
            "order_item",
            "product_name",
            "variant_name",
            "quantity",
            "requested_refund_amount",
            "approved_refund_amount",
        )


class ReturnRequestMediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReturnRequestMedia
        fields = ("id", "media_type", "file_url", "created_at")


class ReturnRequestSerializer(serializers.ModelSerializer):
    items = ReturnRequestItemSerializer(many=True, read_only=True)
    media = ReturnRequestMediaSerializer(many=True, read_only=True)
    shop_order_code = serializers.CharField(source="shop_order.shop_order_code", read_only=True)
    shop_name = serializers.CharField(source="shop_order.shop.name", read_only=True)
    customer_email = serializers.EmailField(source="customer.email", read_only=True)

    class Meta:
        model = ReturnRequest
        fields = (
            "id",
            "shop_order",
            "shop_order_code",
            "shop_name",
            "customer_email",
            "status",
            "reason_code",
            "reason_detail",
            "seller_response",
            "requested_at",
            "resolved_at",
            "items",
            "media",
            "created_at",
            "updated_at",
        )


class SellerReturnDecisionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=("APPROVE", "REJECT"))
    response = serializers.CharField(min_length=1, max_length=5000)


class DisputeEvidenceSerializer(serializers.ModelSerializer):
    submitted_by_email = serializers.EmailField(source="submitted_by.email", read_only=True)

    class Meta:
        model = DisputeEvidence
        fields = ("id", "submitted_by_email", "content", "file_url", "created_at")


class DisputeSerializer(serializers.ModelSerializer):
    return_request = ReturnRequestSerializer(read_only=True)
    evidence = DisputeEvidenceSerializer(many=True, read_only=True)
    assigned_admin_email = serializers.EmailField(source="assigned_admin.email", read_only=True)

    class Meta:
        model = Dispute
        fields = (
            "id",
            "return_request",
            "shop_order",
            "status",
            "decision",
            "decision_note",
            "refund_amount",
            "assigned_admin_email",
            "evidence",
            "resolved_at",
            "created_at",
            "updated_at",
        )


class DisputeResolutionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=Dispute.Decision.choices)
    note = serializers.CharField(min_length=1, max_length=5000)
    refund_amount = serializers.DecimalField(
        max_digits=18, decimal_places=0, min_value=1, required=False
    )

    def validate(self, attrs):
        decision = attrs.get("decision")
        amount = attrs.get("refund_amount")
        if decision == Dispute.Decision.REFUND_PARTIAL and amount is None:
            raise serializers.ValidationError({"refund_amount": "Cần nhập số tiền hoàn một phần"})
        if decision != Dispute.Decision.REFUND_PARTIAL and amount is not None:
            raise serializers.ValidationError(
                {"refund_amount": "Chỉ nhập số tiền khi hoàn một phần"}
            )
        return attrs
