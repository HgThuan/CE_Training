import uuid

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiTypes, extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.views import APIView

from apps.account.permissions import IsCustomer
from apps.cart.models import CartItem
from apps.cart.serializers import (
    CartItemAddSerializer,
    CartItemUpdateSerializer,
    CartMergeSerializer,
    CartPreviewSerializer,
)
from apps.cart.services import CartService
from apps.common.responses import success_response
from apps.product.models import ProductVariant


class CustomerCartMixin:
    permission_classes = [IsCustomer]

    @staticmethod
    def cart(request: Request):
        return CartService.get_or_create_customer_cart(request.user)


class CartDetailView(CustomerCartMixin, APIView):
    @extend_schema(summary="Xem giỏ hàng nhóm theo shop", responses={200: OpenApiTypes.OBJECT})
    def get(self, request: Request):
        data = CartService.get_cart_summary(self.cart(request))
        return success_response(data=data, message="Lấy giỏ hàng thành công")


class CartItemCreateView(CustomerCartMixin, APIView):
    @extend_schema(request=CartItemAddSerializer, responses={201: OpenApiTypes.OBJECT})
    def post(self, request: Request):
        serializer = CartItemAddSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        variant = get_object_or_404(
            ProductVariant.objects.select_related(
                "product",
                "shop",
                "inventory_balance",
            ),
            pk=serializer.validated_data["variant_id"],
        )
        cart = self.cart(request)
        CartService.add_item(
            cart,
            variant,
            serializer.validated_data["quantity"],
            is_selected=serializer.validated_data["is_selected"],
        )
        return success_response(
            data=CartService.get_cart_summary(cart),
            message="Đã thêm sản phẩm vào giỏ",
            status_code=status.HTTP_201_CREATED,
        )


class CartItemUpdateDeleteView(CustomerCartMixin, APIView):
    def _item(self, request: Request, item_id: uuid.UUID) -> CartItem:
        return get_object_or_404(
            CartItem.objects.select_related(
                "variant__inventory_balance",
                "variant__product",
                "variant__shop",
            ),
            pk=item_id,
            cart=self.cart(request),
        )

    @extend_schema(request=CartItemUpdateSerializer, responses={200: OpenApiTypes.OBJECT})
    def patch(self, request: Request, item_id: uuid.UUID):
        serializer = CartItemUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        item = self._item(request, item_id)
        CartService.update_item(item, **serializer.validated_data)
        return success_response(
            data=CartService.get_cart_summary(item.cart),
            message="Cập nhật giỏ hàng thành công",
        )

    def delete(self, request: Request, item_id: uuid.UUID):
        item = self._item(request, item_id)
        cart = item.cart
        item.delete()
        return success_response(
            data=CartService.get_cart_summary(cart),
            message="Đã xóa sản phẩm khỏi giỏ",
        )


class CartMergeView(CustomerCartMixin, APIView):
    @extend_schema(request=CartMergeSerializer, responses={200: OpenApiTypes.OBJECT})
    def post(self, request: Request):
        serializer = CartMergeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        cart = CartService.merge_guest_cart(serializer.validated_data["items"], request.user)
        return success_response(
            data=CartService.get_cart_summary(cart),
            message="Đã gộp giỏ hàng khách",
        )


class CartPreviewView(CustomerCartMixin, APIView):
    @extend_schema(request=CartPreviewSerializer, responses={200: OpenApiTypes.OBJECT})
    def post(self, request: Request):
        serializer = CartPreviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = CartService.preview_checkout(
            self.cart(request),
            serializer.validated_data.get("selected_item_ids"),
            serializer.validated_data.get("voucher_codes"),
        )
        return success_response(data=data, message="Tính giá tạm tính thành công")
