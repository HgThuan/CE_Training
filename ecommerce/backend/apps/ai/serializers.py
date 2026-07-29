from rest_framework import serializers

from apps.product.serializers import (
    ProductPaginationMetaSerializer,
    PublicProductListSerializer,
    SearchFilterSerializer,
)


class AISearchQuerySerializer(SearchFilterSerializer):
    q = serializers.CharField(
        min_length=1,
        max_length=500,
        trim_whitespace=True,
    )


class SmartSearchQuerySerializer(AISearchQuerySerializer):
    pass


class SemanticSearchQuerySerializer(AISearchQuerySerializer):
    pass


class AISearchDataSerializer(serializers.Serializer):
    results = PublicProductListSerializer(many=True)
    explanation = serializers.CharField()
    intent = serializers.DictField()
    ai_used = serializers.BooleanField()
    fallback_used = serializers.BooleanField()


class AISearchResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    data = AISearchDataSerializer()
    meta = ProductPaginationMetaSerializer()
