from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.views import APIView

from apps.account.permissions import IsAdmin, IsCustomer, IsSeller
from apps.common.pagination import StandardPagination
from apps.common.responses import success_response
from apps.order.selectors import get_orders_for_customer

from .selectors import (
    dispute_graph,
    get_disputes_for_admin,
    get_return_requests_for_customer,
    get_return_requests_for_seller,
    return_request_graph,
)
from .serializers import (
    DisputeResolutionSerializer,
    DisputeSerializer,
    ReturnRequestCreateSerializer,
    ReturnRequestSerializer,
    SellerReturnDecisionSerializer,
)
from .services import DisputeService, ReturnRequestService


def _page(view, queryset, serializer):
    paginator = StandardPagination()
    page = paginator.paginate_queryset(queryset, view.request, view=view)
    return paginator.get_paginated_response(serializer(page, many=True).data)


class CustomerReturnRequestView(APIView):
    permission_classes = [IsCustomer]

    def post(self, request, order_id):
        order = get_object_or_404(get_orders_for_customer(request.user), pk=order_id)
        serializer = ReturnRequestCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        shop_order = get_object_or_404(
            order.shop_orders, pk=serializer.validated_data.pop("shop_order_id")
        )
        return_request = ReturnRequestService.create(
            shop_order=shop_order, customer=request.user, **serializer.validated_data
        )
        return_request = return_request_graph().get(pk=return_request.pk)
        return success_response(
            data=ReturnRequestSerializer(return_request).data,
            message="Đã gửi yêu cầu trả hàng",
            status_code=status.HTTP_201_CREATED,
        )

    def get(self, request, order_id):
        order = get_object_or_404(get_orders_for_customer(request.user), pk=order_id)
        requests = get_return_requests_for_customer(request.user).filter(shop_order__order=order)
        return success_response(data=ReturnRequestSerializer(requests, many=True).data)


class CustomerReturnEscalateView(APIView):
    permission_classes = [IsCustomer]

    def post(self, request, return_request_id):
        return_request = get_object_or_404(
            get_return_requests_for_customer(request.user), pk=return_request_id
        )
        dispute = ReturnRequestService.escalate(return_request, customer=request.user)
        return success_response(
            data=DisputeSerializer(dispute_graph().get(pk=dispute.pk)).data,
            message="Đã chuyển khiếu nại đến Admin",
        )


class SellerReturnRequestListView(APIView):
    permission_classes = [IsSeller]

    def get(self, request):
        return _page(
            self,
            get_return_requests_for_seller(request.user, status=request.query_params.get("status")),
            ReturnRequestSerializer,
        )


class SellerReturnDecisionView(APIView):
    permission_classes = [IsSeller]

    def post(self, request, return_request_id):
        return_request = get_object_or_404(
            get_return_requests_for_seller(request.user), pk=return_request_id
        )
        serializer = SellerReturnDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = ReturnRequestService.seller_decide(
            return_request, seller=request.user, **serializer.validated_data
        )
        return success_response(
            data=ReturnRequestSerializer(return_request_graph().get(pk=result.pk)).data,
            message="Đã xử lý yêu cầu",
        )


class AdminDisputeListView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        return _page(
            self,
            get_disputes_for_admin(status=request.query_params.get("status")),
            DisputeSerializer,
        )


class AdminDisputeDetailView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request, dispute_id):
        dispute = get_object_or_404(get_disputes_for_admin(), pk=dispute_id)
        return success_response(data=DisputeSerializer(dispute_graph().get(pk=dispute.pk)).data)


class AdminDisputeReviewView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request, dispute_id):
        dispute = get_object_or_404(get_disputes_for_admin(), pk=dispute_id)
        dispute = DisputeService.start_review(dispute, admin=request.user)
        return success_response(
            data=DisputeSerializer(dispute_graph().get(pk=dispute.pk)).data,
            message="Đã tiếp nhận tranh chấp",
        )


class AdminDisputeResolveView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request, dispute_id):
        dispute = get_object_or_404(get_disputes_for_admin(), pk=dispute_id)
        serializer = DisputeResolutionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        dispute = DisputeService.resolve(
            dispute,
            admin=request.user,
            request_id=getattr(request, "request_id", ""),
            **serializer.validated_data,
        )
        return success_response(
            data=DisputeSerializer(dispute_graph().get(pk=dispute.pk)).data,
            message="Quyết định đã được ghi nhận",
        )
