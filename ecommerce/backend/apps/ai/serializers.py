from uuid import UUID

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


class RecommendationQuerySerializer(serializers.Serializer):
    browsing_history = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=740,
        help_text=(
            "Tối đa 20 UUID sản phẩm, phân tách bằng dấu phẩy và sắp xếp từ mới nhất đến cũ nhất."
        ),
    )
    page = serializers.IntegerField(min_value=1, required=False)
    page_size = serializers.IntegerField(
        min_value=1,
        max_value=100,
        required=False,
    )

    def to_internal_value(self, data):
        unknown = sorted(set(data.keys()) - set(self.fields))
        if unknown:
            raise serializers.ValidationError(
                {"query_params": [f"Tham số không được hỗ trợ: {', '.join(unknown)}"]}
            )
        return super().to_internal_value(data)

    def validate_browsing_history(self, value: str) -> list[UUID]:
        if not value.strip():
            return []
        raw_ids = value.split(",")
        normalized: list[UUID] = []
        seen: set[UUID] = set()
        for raw_id in raw_ids:
            candidate = raw_id.strip()
            if not candidate:
                raise serializers.ValidationError("browsing_history không được chứa phần tử rỗng")
            try:
                product_id = UUID(candidate)
            except ValueError as exc:
                raise serializers.ValidationError(
                    f"UUID sản phẩm không hợp lệ: {candidate[:40]}"
                ) from exc
            if product_id not in seen:
                seen.add(product_id)
                normalized.append(product_id)
        if len(normalized) > 20:
            raise serializers.ValidationError("browsing_history chỉ chấp nhận tối đa 20 sản phẩm")
        return normalized

    def validate(self, attrs):
        attrs = dict(attrs)
        attrs.setdefault("browsing_history", [])
        return attrs


class RecommendationDataSerializer(serializers.Serializer):
    results = PublicProductListSerializer(many=True)
    ai_used = serializers.BooleanField()
    fallback_used = serializers.BooleanField()
    personalized = serializers.BooleanField()
    strategy = serializers.CharField()


class RecommendationResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    data = RecommendationDataSerializer()
    meta = ProductPaginationMetaSerializer()


class SimilarProductsQuerySerializer(serializers.Serializer):
    page = serializers.IntegerField(min_value=1, required=False)
    page_size = serializers.IntegerField(
        min_value=1,
        max_value=100,
        required=False,
    )

    def to_internal_value(self, data):
        unknown = sorted(set(data.keys()) - set(self.fields))
        if unknown:
            raise serializers.ValidationError(
                {"query_params": [f"Tham số không được hỗ trợ: {', '.join(unknown)}"]}
            )
        return super().to_internal_value(data)
