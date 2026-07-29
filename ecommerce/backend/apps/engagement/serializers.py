from django.core.exceptions import ObjectDoesNotExist
from rest_framework import serializers

from .models import ProductAnswer, ProductQuestion
from .services import MAX_QA_CONTENT_LENGTH, MIN_QA_CONTENT_LENGTH


class StrictFieldsMixin:
    def to_internal_value(self, data):
        unknown = sorted(set(data.keys()) - set(self.fields))
        if unknown:
            raise serializers.ValidationError(
                {"fields": [f"Trường không được hỗ trợ: {', '.join(unknown)}"]}
            )
        return super().to_internal_value(data)


class QuestionAuthorSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    full_name = serializers.CharField(read_only=True)
    avatar_url = serializers.URLField(read_only=True, allow_blank=True)


class ProductAnswerSerializer(serializers.ModelSerializer):
    seller = QuestionAuthorSerializer(source="seller_user", read_only=True)

    class Meta:
        model = ProductAnswer
        fields = (
            "id",
            "seller",
            "content",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class ProductQuestionSerializer(serializers.ModelSerializer):
    product_id = serializers.UUIDField(read_only=True)
    customer = QuestionAuthorSerializer(read_only=True)
    answer = serializers.SerializerMethodField()

    class Meta:
        model = ProductQuestion
        fields = (
            "id",
            "product_id",
            "customer",
            "content",
            "status",
            "answer",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_answer(self, question: ProductQuestion) -> dict | None:
        try:
            answer = question.answer
        except ObjectDoesNotExist:
            return None
        return ProductAnswerSerializer(answer).data


class QuestionCreateSerializer(StrictFieldsMixin, serializers.Serializer):
    content = serializers.CharField(
        min_length=MIN_QA_CONTENT_LENGTH,
        max_length=MAX_QA_CONTENT_LENGTH,
        trim_whitespace=True,
        allow_blank=False,
    )


class AnswerCreateSerializer(QuestionCreateSerializer):
    pass


class EngagementPaginationMetaSerializer(serializers.Serializer):
    page = serializers.IntegerField()
    page_size = serializers.IntegerField()
    total_items = serializers.IntegerField()
    total_pages = serializers.IntegerField()


class QuestionListResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    data = ProductQuestionSerializer(many=True)
    meta = EngagementPaginationMetaSerializer()


class QuestionResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    data = ProductQuestionSerializer()


class AnswerResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    data = ProductAnswerSerializer()
