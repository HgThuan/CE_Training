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
    match_reasons = serializers.DictField(child=serializers.CharField())


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
    cart_products = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=740,
        help_text="Tối đa 20 UUID sản phẩm đang có trong giỏ hàng.",
    )
    landing_context = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=40,
        default="home",
    )
    traffic_source = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=80,
        default="direct",
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
        return self._validate_uuid_list(value, field_name="browsing_history")

    def validate_cart_products(self, value: str) -> list[UUID]:
        return self._validate_uuid_list(value, field_name="cart_products")

    @staticmethod
    def _validate_uuid_list(value: str, *, field_name: str) -> list[UUID]:
        if not value.strip():
            return []
        raw_ids = value.split(",")
        normalized: list[UUID] = []
        seen: set[UUID] = set()
        for raw_id in raw_ids:
            candidate = raw_id.strip()
            if not candidate:
                raise serializers.ValidationError(f"{field_name} không được chứa phần tử rỗng")
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
            raise serializers.ValidationError(f"{field_name} chỉ chấp nhận tối đa 20 sản phẩm")
        return normalized

    def validate(self, attrs):
        attrs = dict(attrs)
        attrs.setdefault("browsing_history", [])
        attrs.setdefault("cart_products", [])
        return attrs


class RecommendationDataSerializer(serializers.Serializer):
    results = PublicProductListSerializer(many=True)
    ai_used = serializers.BooleanField()
    fallback_used = serializers.BooleanField()
    personalized = serializers.BooleanField()
    strategy = serializers.CharField()
    recommendation_id = serializers.UUIDField()


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


class RecommendationEventSerializer(serializers.Serializer):
    recommendation_id = serializers.UUIDField()
    product_id = serializers.UUIDField()
    event_type = serializers.ChoiceField(choices=("impression", "click", "add_to_cart"))
    source = serializers.ChoiceField(choices=("home", "product", "similar", "search"))
    position = serializers.IntegerField(min_value=0, max_value=500, required=False)
    visitor_id = serializers.CharField(
        max_length=200,
        required=False,
        allow_blank=True,
        write_only=True,
    )
    context = serializers.DictField(required=False, default=dict)

    def validate_context(self, value):
        if len(value) > 20:
            raise serializers.ValidationError("context chỉ chấp nhận tối đa 20 trường")
        return {
            str(key)[:80]: str(item)[:300]
            for key, item in value.items()
            if isinstance(item, (str, int, float, bool)) or item is None
        }


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


class AssistantMessageRequestSerializer(serializers.Serializer):
    conversation_id = serializers.UUIDField(required=False, allow_null=True)
    guest_token = serializers.RegexField(
        regex=r"^[A-Za-z0-9._-]{20,64}$",
        required=False,
        write_only=True,
    )
    message = serializers.CharField(
        min_length=1,
        max_length=1_000,
        trim_whitespace=True,
    )
    browsing_history = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        max_length=20,
        allow_empty=True,
    )
    channel = serializers.RegexField(
        regex=r"^[a-z][a-z0-9_-]{1,29}$",
        required=False,
        default="web",
    )

    def validate_browsing_history(self, value):
        return list(dict.fromkeys(value))


class AssistantFeedbackSerializer(serializers.Serializer):
    guest_token = serializers.RegexField(
        regex=r"^[A-Za-z0-9._-]{20,64}$",
        required=False,
        write_only=True,
    )
    rating = serializers.IntegerField(min_value=1, max_value=5)
    resolved = serializers.BooleanField(required=False, allow_null=True)
    comment = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=1_000,
        trim_whitespace=True,
    )


class AssistantMessageSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    conversation_id = serializers.UUIDField()
    role = serializers.ChoiceField(choices=("user", "assistant"))
    content = serializers.CharField(allow_blank=True)
    attachments = serializers.ListField(child=serializers.DictField())
    feedback = serializers.DictField(allow_null=True, required=False)
    created_at = serializers.DateTimeField()


class AssistantConversationSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    title = serializers.CharField()
    status = serializers.CharField()
    turn_count = serializers.IntegerField()
    last_active_at = serializers.DateTimeField()
    created_at = serializers.DateTimeField()


class AssistantConversationDetailSerializer(AssistantConversationSerializer):
    messages = AssistantMessageSerializer(many=True)
