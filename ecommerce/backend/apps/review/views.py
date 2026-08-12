from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.views import APIView

from apps.account.permissions import IsAdmin, IsCustomer, IsSeller
from apps.common.pagination import StandardPagination
from apps.common.responses import success_response
from apps.order.models import OrderItem

from .models import Review
from .selectors import (
    get_open_review_reports,
    get_public_product_reviews,
    get_reviews_for_seller,
    review_graph,
)
from .serializers import (
    ReplyWriteSerializer,
    ReportResolutionSerializer,
    ReportWriteSerializer,
    ReviewReportSerializer,
    ReviewSerializer,
    ReviewWriteSerializer,
)
from .services import ReviewService


def _page(view, queryset, serializer):
    paginator = StandardPagination()
    page = paginator.paginate_queryset(queryset, view.request, view=view)
    return paginator.get_paginated_response(serializer(page, many=True).data)


class ProductReviewListView(APIView):
    permission_classes = []
    authentication_classes = []

    def get(self, request, product_id):
        return _page(self, get_public_product_reviews(product_id), ReviewSerializer)


class CustomerReviewCreateView(APIView):
    permission_classes = [IsCustomer]

    def post(self, request, order_item_id):
        item = get_object_or_404(OrderItem, pk=order_item_id)
        serializer = ReviewWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        review = ReviewService.create(
            order_item=item, user=request.user, **serializer.validated_data
        )
        review = review_graph().get(pk=review.pk)
        return success_response(
            data=ReviewSerializer(review).data,
            message="Đã gửi đánh giá",
            status_code=status.HTTP_201_CREATED,
        )


class CustomerReviewUpdateView(APIView):
    permission_classes = [IsCustomer]

    def patch(self, request, review_id):
        review = get_object_or_404(Review, pk=review_id, user=request.user, is_deleted=False)
        serializer = ReviewWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        review = ReviewService.update(review, user=request.user, **serializer.validated_data)
        return success_response(
            data=ReviewSerializer(review_graph().get(pk=review.pk)).data,
            message="Đã cập nhật đánh giá",
        )


class SellerReviewListView(APIView):
    permission_classes = [IsSeller]

    def get(self, request):
        return _page(
            self,
            get_reviews_for_seller(
                request.user,
                rating=request.query_params.get("rating"),
                status=request.query_params.get("status"),
            ),
            ReviewSerializer,
        )


class SellerReviewReplyView(APIView):
    permission_classes = [IsSeller]

    def post(self, request, review_id):
        review = get_object_or_404(get_reviews_for_seller(request.user), pk=review_id)
        serializer = ReplyWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ReviewService.reply(review, seller=request.user, **serializer.validated_data)
        return success_response(
            data=ReviewSerializer(review_graph().get(pk=review.pk)).data, message="Đã lưu phản hồi"
        )


class SellerReviewReportView(APIView):
    permission_classes = [IsSeller]

    def post(self, request, review_id):
        review = get_object_or_404(get_reviews_for_seller(request.user), pk=review_id)
        serializer = ReportWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        report = ReviewService.report(review, seller=request.user, **serializer.validated_data)
        return success_response(
            data={"id": str(report.pk), "status": report.status},
            message="Đã gửi báo cáo",
            status_code=status.HTTP_201_CREATED,
        )


class AdminReviewReportListView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        return _page(self, get_open_review_reports(), ReviewReportSerializer)


class AdminReviewReportResolveView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request, report_id):
        report = get_object_or_404(get_open_review_reports(), pk=report_id)
        serializer = ReportResolutionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        report = ReviewService.resolve_report(
            report, admin=request.user, **serializer.validated_data
        )
        return success_response(
            data=ReviewReportSerializer(report).data, message="Đã xử lý báo cáo"
        )
