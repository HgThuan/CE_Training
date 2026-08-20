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


class ProductAIReviewSummaryDataSerializer(serializers.Serializer):
    summary = serializers.CharField()
    pros = serializers.ListField(child=serializers.CharField())
    cons = serializers.ListField(child=serializers.CharField())
    sentiment = serializers.ChoiceField(choices=("positive", "neutral", "negative"))
    sample_count = serializers.IntegerField(min_value=0)
    is_ai_generated = serializers.BooleanField()
    ai_label = serializers.CharField(allow_null=True)


class ProductAIReviewSummaryResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    data = ProductAIReviewSummaryDataSerializer()


class ProductAISummaryDataSerializer(serializers.Serializer):
    summary = serializers.CharField(allow_blank=True)
    highlights = serializers.ListField(child=serializers.CharField())
    target_audience = serializers.CharField(allow_blank=True)
    key_specs = serializers.DictField(child=serializers.CharField())
    is_ai_generated = serializers.BooleanField()
    ai_label = serializers.CharField(allow_null=True)


class ProductAISummaryResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    data = ProductAISummaryDataSerializer()


class ProductCompareRequestSerializer(serializers.Serializer):
    product_ids = serializers.ListField(child=serializers.UUIDField(), min_length=2, max_length=4)

    def validate_product_ids(self, value):
        if len(set(value)) != len(value):
            raise serializers.ValidationError("Mỗi sản phẩm chỉ được chọn một lần")
        return value


class ProductCompareProductSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()


class ProductCompareRowSerializer(serializers.Serializer):
    label = serializers.CharField()
    values = serializers.ListField(child=serializers.CharField())


class ProductCompareRecommendationSerializer(serializers.Serializer):
    need = serializers.CharField()
    product_index = serializers.IntegerField(min_value=0, max_value=3)
    reason = serializers.CharField()


class ProductCompareDataSerializer(serializers.Serializer):
    products = ProductCompareProductSerializer(many=True)
    rows = ProductCompareRowSerializer(many=True)
    recommendations = ProductCompareRecommendationSerializer(many=True)
    is_comparable = serializers.BooleanField()
    compatibility_message = serializers.CharField(allow_null=True)
    is_ai_generated = serializers.BooleanField()
    ai_label = serializers.CharField(allow_null=True)


class ProductCompareResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    data = ProductCompareDataSerializer()


class SellerListingRequestSerializer(serializers.Serializer):
    name = serializers.CharField(
        max_length=200,
        trim_whitespace=False,
        required=False,
        allow_blank=True,
        default="",
    )
    keywords = serializers.ListField(
        child=serializers.CharField(max_length=50, trim_whitespace=False),
        max_length=10,
        required=False,
        default=list,
    )


class SellerListingDataSerializer(serializers.Serializer):
    title = serializers.CharField()
    description = serializers.CharField()
    meta_description = serializers.CharField()
    is_ai_generated = serializers.BooleanField()
    ai_label = serializers.CharField()


class SellerListingResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    data = SellerListingDataSerializer()


class ChatTurnRequestSerializer(serializers.Serializer):
    session_id = serializers.UUIDField(required=False, allow_null=True)
    guest_token = serializers.RegexField(
        regex=r"^[A-Za-z0-9._-]{20,64}$",
        required=False,
        allow_blank=False,
    )
    message = serializers.CharField(
        min_length=1,
        max_length=1_000,
        trim_whitespace=True,
    )


class ChatMessageSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    session_id = serializers.UUIDField()
    role = serializers.ChoiceField(choices=("user", "assistant"))
    content = serializers.CharField(allow_blank=True)
    attachments = serializers.ListField(child=serializers.DictField())
    created_at = serializers.DateTimeField()


class ChatMessageHistoryResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    data = ChatMessageSerializer(many=True)
