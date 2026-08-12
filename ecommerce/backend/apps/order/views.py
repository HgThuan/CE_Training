from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from rest_framework import status
from rest_framework.views import APIView

from apps.account.permissions import IsAdmin, IsCustomer, IsSeller
from apps.cart.services import CartService
from apps.common.pagination import StandardPagination
from apps.common.responses import success_response

from .models import ShopOrder
from .selectors import get_all_orders_for_admin, get_orders_for_customer, get_shop_orders_for_seller
from .serializers import (
    CancelSerializer,
    CheckoutPreviewSerializer,
    CheckoutSerializer,
    OrderSerializer,
    ShopOrderDetailSerializer,
)
from .services import CheckoutService, OrderService


def _page(view, queryset, serializer):
    paginator = StandardPagination()
    page = paginator.paginate_queryset(queryset, view.request, view=view)
    return paginator.get_paginated_response(serializer(page, many=True).data)


class CheckoutPreviewView(APIView):
    permission_classes = [IsCustomer]

    def post(self, request):
        serializer = CheckoutPreviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        customer = CartService.get_or_create_customer_cart(request.user).user
        data = CheckoutService.preview(
            customer=customer,
            cart_item_ids=serializer.validated_data.get("cart_item_ids"),
            coupons=serializer.validated_data.get("coupons"),
        )
        return success_response(data=data, message="Tính checkout thành công")


class CheckoutConfirmView(APIView):
    permission_classes = [IsCustomer]

    def post(self, request):
        serializer = CheckoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        customer = CartService.get_or_create_customer_cart(request.user).user
        order, payment_url, created = CheckoutService.checkout(
            customer=customer,
            idempotency_key=request.headers.get("Idempotency-Key"),
            **serializer.validated_data,
        )
        data = OrderSerializer(order).data
        data["orders"] = [
            {
                "order_id": str(item.pk),
                "order_code": item.shop_order_code,
                "shop_id": item.shop_id,
                "total_amount": item.total_amount,
            }
            for item in order.shop_orders.all()
        ]
        data["payment_redirect_url"] = payment_url
        return success_response(
            data=data,
            message="Đặt hàng thành công",
            status_code=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class CustomerOrderListView(APIView):
    permission_classes = [IsCustomer]

    def get(self, request):
        return _page(
            self,
            get_orders_for_customer(request.user, status=request.query_params.get("status")),
            OrderSerializer,
        )


class CustomerOrderDetailView(APIView):
    permission_classes = [IsCustomer]

    def get(self, request, order_id):
        order = get_object_or_404(get_orders_for_customer(request.user), pk=order_id)
        return success_response(data=OrderSerializer(order).data)


class CustomerOrderCancelView(APIView):
    permission_classes = [IsCustomer]

    def post(self, request, order_id):
        order = get_object_or_404(get_orders_for_customer(request.user), pk=order_id)
        serializer = CancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        shop_order = get_object_or_404(
            order.shop_orders,
            pk=serializer.validated_data.get("shop_order_id"),
        )
        OrderService.cancel(
            shop_order,
            request.user,
            serializer.validated_data["reason_code"],
            serializer.validated_data.get("reason_detail", ""),
        )
        return success_response(data=OrderSerializer(order).data, message="Đã hủy đơn của shop")


class CustomerOrderReorderView(APIView):
    permission_classes = [IsCustomer]

    def post(self, request, order_id):
        order = get_object_or_404(get_orders_for_customer(request.user), pk=order_id)
        skipped = OrderService.reorder(order, order.customer)
        cart = CartService.get_or_create_customer_cart(request.user)
        return success_response(
            data={"cart": CartService.get_cart_summary(cart), "skipped_items": skipped},
            message="Đã thêm lại các sản phẩm còn khả dụng",
        )


class SellerOrderListView(APIView):
    permission_classes = [IsSeller]

    def get(self, request):
        return _page(
            self,
            get_shop_orders_for_seller(request.user, status=request.query_params.get("status")),
            ShopOrderDetailSerializer,
        )


class SellerOrderDetailView(APIView):
    permission_classes = [IsSeller]

    def get(self, request, shop_order_id):
        item = get_object_or_404(get_shop_orders_for_seller(request.user), pk=shop_order_id)
        return success_response(data=ShopOrderDetailSerializer(item).data)


class SellerOrderActionView(APIView):
    permission_classes = [IsSeller]
    action = ""

    def post(self, request, shop_order_id):
        item = get_object_or_404(get_shop_orders_for_seller(request.user), pk=shop_order_id)
        reason = str(request.data.get("reason", ""))
        if self.action == "confirm":
            item = OrderService.confirm(item, request.user)
        elif self.action == "cancel":
            item = OrderService.cancel(
                item, request.user, request.data.get("reason_code", "SELLER_CANCEL"), reason
            )
        else:
            target = {
                "pack": ShopOrder.FulfillmentStatus.PACKING,
                "ship": ShopOrder.FulfillmentStatus.SHIPPING,
            }.get(self.action)
            if self.action == "complete":
                if item.fulfillment_status == ShopOrder.FulfillmentStatus.SHIPPING:
                    item = OrderService.transition_status(
                        item, ShopOrder.FulfillmentStatus.DELIVERED, request.user, reason
                    )
                target = ShopOrder.FulfillmentStatus.COMPLETED
            item = OrderService.transition_status(item, target, request.user, reason)
        return success_response(
            data=ShopOrderDetailSerializer(item).data, message="Đã cập nhật đơn"
        )


class ConfirmOrderView(SellerOrderActionView):
    action = "confirm"


class PackOrderView(SellerOrderActionView):
    action = "pack"


class ShipOrderView(SellerOrderActionView):
    action = "ship"


class CompleteOrderView(SellerOrderActionView):
    action = "complete"


class CancelSellerOrderView(SellerOrderActionView):
    action = "cancel"


class PackingSlipView(APIView):
    permission_classes = [IsSeller]

    def get(self, request, shop_order_id):
        from django.http import HttpResponse

        item = get_object_or_404(get_shop_orders_for_seller(request.user), pk=shop_order_id)
        html = render_to_string("order/packing_slip.html", {"shop_order": item})
        return HttpResponse(html, content_type="text/html; charset=utf-8")


class AdminOrderListView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        queryset = get_all_orders_for_admin(
            status=request.query_params.get("status"),
            seller=request.query_params.get("seller"),
            date_from=request.query_params.get("date_from"),
            date_to=request.query_params.get("date_to"),
            search=request.query_params.get("search"),
        )
        return _page(self, queryset, OrderSerializer)


class AdminOrderDetailView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request, order_id):
        order = get_object_or_404(get_all_orders_for_admin(), pk=order_id)
        return success_response(data=OrderSerializer(order).data)
