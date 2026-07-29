from drf_spectacular.utils import extend_schema
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from apps.common.responses import success_response

from .customer_selectors import get_wishlist_items
from .customer_serializers import (
    EmptyInputSerializer,
    ShopFollowResponseSerializer,
    WishlistItemSerializer,
    WishlistListResponseSerializer,
    WishlistToggleResponseSerializer,
    WishlistToggleSerializer,
)
from .customer_services import ShopFollowService, WishlistService
from .permissions import IsActiveCustomer


class WishlistListView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated, IsActiveCustomer]
    serializer_class = WishlistItemSerializer

    @extend_schema(
        operation_id="customer_wishlist_list",
        responses={200: WishlistListResponseSerializer},
    )
    def get(self, request):
        page = self.paginate_queryset(get_wishlist_items(customer=request.user))
        return self.get_paginated_response(
            self.get_serializer(page, many=True).data,
        )


class WishlistToggleView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated, IsActiveCustomer]
    serializer_class = WishlistToggleSerializer

    @extend_schema(
        operation_id="customer_wishlist_toggle",
        request=WishlistToggleSerializer,
        responses={200: WishlistToggleResponseSerializer},
    )
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = WishlistService.toggle(
            customer=request.user,
            product_id=serializer.validated_data["product_id"],
        )
        return success_response(
            message=(
                "Đã thêm sản phẩm vào wishlist"
                if result.is_wishlisted
                else "Đã xóa sản phẩm khỏi wishlist"
            ),
            data={
                "product_id": str(result.product_id),
                "is_wishlisted": result.is_wishlisted,
                "item": (
                    WishlistItemSerializer(result.item).data if result.item is not None else None
                ),
            },
        )


class ShopFollowToggleView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated, IsActiveCustomer]
    serializer_class = EmptyInputSerializer

    @extend_schema(
        operation_id="customer_shop_follow_toggle",
        request=None,
        responses={200: ShopFollowResponseSerializer},
    )
    def post(self, request, shop_id: int):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = ShopFollowService.toggle(
            customer=request.user,
            shop_id=shop_id,
        )
        return success_response(
            message=(
                "Đã theo dõi gian hàng" if result.is_following else "Đã bỏ theo dõi gian hàng"
            ),
            data={
                "shop_id": result.shop_id,
                "is_following": result.is_following,
                "follower_count": result.follower_count,
            },
        )
