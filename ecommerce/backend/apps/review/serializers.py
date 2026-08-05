from rest_framework import serializers

from .models import Review, ReviewMedia, ReviewReply, ReviewReport


class ReviewMediaInputSerializer(serializers.Serializer):
    media_type = serializers.ChoiceField(choices=ReviewMedia.MediaType.choices)
    file_url = serializers.URLField(max_length=1000)


class ReviewWriteSerializer(serializers.Serializer):
    rating = serializers.IntegerField(min_value=1, max_value=5)
    content = serializers.CharField(required=False, allow_blank=True, max_length=5000)
    media = ReviewMediaInputSerializer(many=True, required=False)

    def validate_media(self, value):
        images = sum(item["media_type"] == ReviewMedia.MediaType.IMAGE for item in value)
        videos = sum(item["media_type"] == ReviewMedia.MediaType.VIDEO for item in value)
        if images > 5 or videos > 1:
            raise serializers.ValidationError("Tối đa 5 ảnh và 1 video cho mỗi đánh giá")
        return value


class ReviewMediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReviewMedia
        fields = ("id", "media_type", "file_url", "sort_order")


class ReviewReplySerializer(serializers.ModelSerializer):
    seller_name = serializers.CharField(source="seller_user.full_name", read_only=True)

    class Meta:
        model = ReviewReply
        fields = ("id", "seller_name", "content", "created_at", "updated_at")


class ReviewSerializer(serializers.ModelSerializer):
    media = ReviewMediaSerializer(many=True, read_only=True)
    reply = ReviewReplySerializer(read_only=True)
    customer_name = serializers.CharField(source="user.full_name", read_only=True)
    product_name = serializers.CharField(source="product.name", read_only=True)
    order_code = serializers.CharField(
        source="order_item.shop_order.order.order_code", read_only=True
    )

    class Meta:
        model = Review
        fields = (
            "id",
            "order_item",
            "product",
            "product_name",
            "order_code",
            "customer_name",
            "rating",
            "content",
            "is_verified_purchase",
            "status",
            "editable_until",
            "media",
            "reply",
            "created_at",
            "updated_at",
        )


class ReplyWriteSerializer(serializers.Serializer):
    content = serializers.CharField(min_length=1, max_length=5000, trim_whitespace=True)


class ReportWriteSerializer(serializers.Serializer):
    reason_code = serializers.CharField(min_length=1, max_length=50)
    reason_detail = serializers.CharField(required=False, allow_blank=True, max_length=2000)


class ReviewReportSerializer(serializers.ModelSerializer):
    review = ReviewSerializer(read_only=True)
    reporter_email = serializers.EmailField(source="reported_by.email", read_only=True)

    class Meta:
        model = ReviewReport
        fields = (
            "id",
            "review",
            "reporter_email",
            "reason_code",
            "reason_detail",
            "status",
            "resolution_note",
            "created_at",
            "updated_at",
        )


class ReportResolutionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=("HIDE", "KEEP"))
    note = serializers.CharField(required=False, allow_blank=True, max_length=2000)
