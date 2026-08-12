from rest_framework import serializers

from .models import Payment


class PaymentStatusSerializer(serializers.ModelSerializer):
    order_id = serializers.UUIDField(source="order.id")
    order_code = serializers.CharField(source="order.order_code")

    class Meta:
        model = Payment
        fields = (
            "id",
            "order_id",
            "order_code",
            "payment_code",
            "method",
            "provider",
            "amount",
            "currency",
            "status",
            "paid_at",
            "failed_at",
            "created_at",
        )
