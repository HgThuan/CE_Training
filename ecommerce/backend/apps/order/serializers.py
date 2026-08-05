from rest_framework import serializers

from apps.review.serializers import ReviewSerializer

from .models import Order, OrderAddress, OrderItem, OrderStatusHistory, ShopOrder


class CheckoutSerializer(serializers.Serializer):
    address_id = serializers.IntegerField()
    payment_method = serializers.CharField()
    coupons = serializers.JSONField(required=False, default=dict)
    cart_item_ids = serializers.ListField(
        child=serializers.UUIDField(), required=False, allow_empty=False
    )
    checkout_note = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_payment_method(self, value):
        normalized = value.strip().upper()
        if normalized not in Order.PaymentMethod.values:
            raise serializers.ValidationError("Phương thức thanh toán không hợp lệ")
        return normalized


class CheckoutPreviewSerializer(serializers.Serializer):
    address_id = serializers.IntegerField(required=False)
    coupons = serializers.JSONField(required=False, default=dict)
    cart_item_ids = serializers.ListField(
        child=serializers.UUIDField(), required=False, allow_empty=False
    )


class OrderAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderAddress
        exclude = ("order", "updated_at")


class OrderItemSerializer(serializers.ModelSerializer):
    review = ReviewSerializer(read_only=True, allow_null=True)

    class Meta:
        model = OrderItem
        fields = (
            "id",
            "product_name",
            "variant_name",
            "sku",
            "variant_attributes",
            "product_image_url",
            "unit_original_price",
            "unit_sale_price",
            "quantity",
            "line_subtotal",
            "shop_discount",
            "platform_discount",
            "line_total",
            "review",
        )


class OrderStatusHistorySerializer(serializers.ModelSerializer):
    changed_by = serializers.CharField(source="changed_by.email", allow_null=True)

    class Meta:
        model = OrderStatusHistory
        fields = (
            "id",
            "from_status",
            "to_status",
            "changed_by",
            "reason",
            "metadata",
            "created_at",
        )


class ShopOrderSerializer(serializers.ModelSerializer):
    shop_name = serializers.CharField(source="shop.name")
    items = OrderItemSerializer(many=True)
    status_history = OrderStatusHistorySerializer(many=True)

    class Meta:
        model = ShopOrder
        fields = (
            "id",
            "shop_order_code",
            "shop",
            "shop_name",
            "fulfillment_status",
            "subtotal",
            "shop_discount",
            "platform_discount_allocated",
            "shipping_fee",
            "total_amount",
            "shipping_method_code",
            "shipping_method_name",
            "seller_note",
            "confirmed_at",
            "delivered_at",
            "completed_at",
            "cod_collected_at",
            "items",
            "status_history",
            "created_at",
            "updated_at",
        )


class OrderSerializer(serializers.ModelSerializer):
    shipping_address = OrderAddressSerializer()
    shop_orders = ShopOrderSerializer(many=True)

    class Meta:
        model = Order
        fields = (
            "id",
            "order_code",
            "currency",
            "subtotal",
            "platform_discount",
            "shop_discount_total",
            "shipping_total",
            "grand_total",
            "payment_status",
            "payment_method",
            "checkout_note",
            "placed_at",
            "expires_at",
            "shipping_address",
            "shop_orders",
            "created_at",
            "updated_at",
        )


class ShopOrderDetailSerializer(ShopOrderSerializer):
    order_code = serializers.CharField(source="order.order_code")
    payment_method = serializers.CharField(source="order.payment_method")
    payment_status = serializers.CharField(source="order.payment_status")
    customer_email = serializers.EmailField(source="order.customer.user.email")
    shipping_address = OrderAddressSerializer(source="order.shipping_address")

    class Meta(ShopOrderSerializer.Meta):
        fields = ShopOrderSerializer.Meta.fields + (
            "order_code",
            "payment_method",
            "payment_status",
            "customer_email",
            "shipping_address",
        )


class CancelSerializer(serializers.Serializer):
    shop_order_id = serializers.UUIDField(required=False)
    reason_code = serializers.CharField(max_length=50)
    reason_detail = serializers.CharField(required=False, allow_blank=True, default="")


class SellerCustomerSerializer(serializers.Serializer):
    id = serializers.IntegerField(source="order__customer__user_id")
    email = serializers.EmailField(source="order__customer__user__email")
    full_name = serializers.CharField(source="order__customer__user__full_name")
    order_count = serializers.IntegerField()
    total_spent = serializers.DecimalField(max_digits=18, decimal_places=0)
    last_order_at = serializers.DateTimeField()
