from rest_framework import serializers

from apps.catalog.serializers import CategoryTreeSerializer
from apps.product.serializers import PublicProductListSerializer

from .models import Banner


class BannerAdminSerializer(serializers.ModelSerializer):
    title = serializers.CharField(
        max_length=180,
        allow_blank=True,
        allow_null=True,
        required=False,
    )
    image_url = serializers.URLField(max_length=2000)
    target_url = serializers.URLField(
        max_length=2000,
        allow_blank=True,
        allow_null=True,
        required=False,
    )
    sort_order = serializers.IntegerField(min_value=0, required=False)

    class Meta:
        model = Banner
        fields = (
            "id",
            "title",
            "image_url",
            "target_url",
            "position",
            "sort_order",
            "starts_at",
            "ends_at",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")
        extra_kwargs = {
            "title": {"required": False, "allow_blank": True},
            "position": {"required": False},
            "starts_at": {"required": False, "allow_null": True},
            "ends_at": {"required": False, "allow_null": True},
            "is_active": {"required": False},
        }

    def validate(self, attrs):
        for field in ("title", "target_url"):
            if field in attrs and attrs[field] is None:
                attrs[field] = ""
        starts_at = attrs.get("starts_at", getattr(self.instance, "starts_at", None))
        ends_at = attrs.get("ends_at", getattr(self.instance, "ends_at", None))
        if starts_at and ends_at and ends_at <= starts_at:
            raise serializers.ValidationError(
                {"ends_at": "Thời gian kết thúc phải sau thời gian bắt đầu"}
            )
        if self.instance is not None and not attrs:
            raise serializers.ValidationError("Cần cung cấp ít nhất một trường để cập nhật")
        return attrs


class BannerPublicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Banner
        fields = ("id", "title", "image_url", "target_url", "position", "sort_order")
        read_only_fields = fields


class BannerReorderSerializer(serializers.Serializer):
    source_id = serializers.UUIDField()
    target_id = serializers.UUIDField()

    def validate(self, attrs):
        if attrs["source_id"] == attrs["target_id"]:
            raise serializers.ValidationError("Banner nguồn và đích phải khác nhau")
        return attrs


class StorefrontPaginationMetaSerializer(serializers.Serializer):
    page = serializers.IntegerField()
    page_size = serializers.IntegerField()
    total_items = serializers.IntegerField()
    total_pages = serializers.IntegerField()


class BannerResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    data = BannerAdminSerializer()


class BannerListResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    data = BannerAdminSerializer(many=True)
    meta = StorefrontPaginationMetaSerializer()


class BannerReorderResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    data = BannerAdminSerializer(many=True)


class BannerDeleteDataSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    is_deleted = serializers.BooleanField()


class BannerDeleteResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    data = BannerDeleteDataSerializer()


class HomeDataSerializer(serializers.Serializer):
    banners = BannerPublicSerializer(many=True)
    new_arrivals = PublicProductListSerializer(many=True)
    best_sellers = PublicProductListSerializer(many=True)
    categories = CategoryTreeSerializer(many=True)


class HomeResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    data = HomeDataSerializer()
