from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated

from apps.common.exceptions import BusinessError
from apps.common.responses import success_response

from .permissions import IsActiveCustomer, IsActiveSeller
from .selectors import get_public_product, get_public_questions
from .serializers import (
    AnswerCreateSerializer,
    AnswerResponseSerializer,
    ProductAnswerSerializer,
    ProductQuestionSerializer,
    QuestionCreateSerializer,
    QuestionListResponseSerializer,
    QuestionResponseSerializer,
)
from .services import AnswerService, QuestionService


class ProductQuestionListCreateView(generics.GenericAPIView):
    serializer_class = QuestionCreateSerializer

    def get_permissions(self):
        if self.request.method == "GET":
            return [AllowAny()]
        return [IsAuthenticated(), IsActiveCustomer()]

    @staticmethod
    def get_product(product_id):
        product = get_public_product(product_id)
        if product is None:
            raise BusinessError("Không tìm thấy sản phẩm", http_status=404)
        return product

    @extend_schema(
        operation_id="public_product_questions_list",
        responses={200: QuestionListResponseSerializer},
    )
    def get(self, request, product_id):
        product = self.get_product(product_id)
        page = self.paginate_queryset(get_public_questions(product=product))
        data = ProductQuestionSerializer(page, many=True).data
        return self.get_paginated_response(data)

    @extend_schema(
        operation_id="customer_product_questions_create",
        request=QuestionCreateSerializer,
        responses={201: QuestionResponseSerializer},
    )
    def post(self, request, product_id):
        product = self.get_product(product_id)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        question = QuestionService.create(
            customer=request.user,
            product=product,
            content=serializer.validated_data["content"],
        )
        return success_response(
            message="Đặt câu hỏi thành công",
            data=ProductQuestionSerializer(question).data,
            status_code=status.HTTP_201_CREATED,
        )


class ProductAnswerCreateView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated, IsActiveSeller]
    serializer_class = AnswerCreateSerializer

    @extend_schema(
        operation_id="seller_product_answers_create",
        request=AnswerCreateSerializer,
        responses={201: AnswerResponseSerializer},
    )
    def post(self, request, question_id):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        answer = AnswerService.create(
            seller_user=request.user,
            question_id=question_id,
            content=serializer.validated_data["content"],
        )
        return success_response(
            message="Trả lời câu hỏi thành công",
            data=ProductAnswerSerializer(answer).data,
            status_code=status.HTTP_201_CREATED,
        )
