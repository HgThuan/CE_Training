from rest_framework import serializers

from apps.product.serializers import PublicProductListSerializer

from .models import WishlistItem
from .serializers import EngagementPaginationMetaSerializer, StrictFieldsMixin


class WishlistItemSerializer(serializers.ModelSerializer):
    product = PublicProductListSerializer(read_only=True)

    class Meta:
        model = WishlistItem
        fields = (
            "id",
            "product",
            "price_when_added",
            "created_at",
        )
        read_only_fields = fields


class WishlistToggleSerializer(StrictFieldsMixin, serializers.Serializer):
    product_id = serializers.UUIDField()


class EmptyInputSerializer(StrictFieldsMixin, serializers.Serializer):
    pass


class WishlistToggleDataSerializer(serializers.Serializer):
    product_id = serializers.UUIDField()
    is_wishlisted = serializers.BooleanField()
    item = WishlistItemSerializer(allow_null=True)


class ShopFollowDataSerializer(serializers.Serializer):
    shop_id = serializers.IntegerField()
    is_following = serializers.BooleanField()
    follower_count = serializers.IntegerField()


class WishlistListResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    data = WishlistItemSerializer(many=True)
    meta = EngagementPaginationMetaSerializer()


class WishlistToggleResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    data = WishlistToggleDataSerializer()


class ShopFollowResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    data = ShopFollowDataSerializer()
