from drf_spectacular.utils import extend_schema
from rest_framework import generics
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from apps.catalog.serializers import CategoryTreeSerializer
from apps.common.cache_utils import (
    HOME_PAGE_CACHE_KEY,
    HOME_PAGE_CACHE_TTL,
    safe_cache_get,
    safe_cache_set,
)
from apps.common.exceptions import BusinessError
from apps.common.responses import success_response
from apps.product.serializers import PublicProductListSerializer
from apps.promotion.services import FlashSaleService

from .permissions import IsAdmin
from .selectors import (
    get_active_banners,
    get_admin_banners,
    get_banner_for_admin,
    get_home_categories,
    get_home_products,
)
from .serializers import (
    BannerAdminSerializer,
    BannerDeleteResponseSerializer,
    BannerListResponseSerializer,
    BannerPublicSerializer,
    BannerReorderResponseSerializer,
    BannerReorderSerializer,
    BannerResponseSerializer,
    HomeResponseSerializer,
)
from .services import BannerService


class AdminBannerListCreateView(generics.GenericAPIView):
    permission_classes = [IsAdmin]
    serializer_class = BannerAdminSerializer

    @extend_schema(
        operation_id="admin_banners_list",
        responses={200: BannerListResponseSerializer},
    )
    def get(self, request):
        page = self.paginate_queryset(get_admin_banners())
        return self.get_paginated_response(BannerAdminSerializer(page, many=True).data)

    @extend_schema(
        operation_id="admin_banners_create",
        request=BannerAdminSerializer,
        responses={201: BannerResponseSerializer},
    )
    def post(self, request):
        serializer = BannerAdminSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        banner = BannerService.create(data=dict(serializer.validated_data))
        return success_response(
            message="Tạo banner thành công",
            data=BannerAdminSerializer(banner).data,
            status_code=201,
        )


class AdminBannerDetailView(APIView):
    permission_classes = [IsAdmin]

    @staticmethod
    def get_banner(banner_id):
        banner = get_banner_for_admin(banner_id)
        if banner is None:
            raise BusinessError("Không tìm thấy banner", http_status=404)
        return banner

    @extend_schema(
        operation_id="admin_banners_retrieve",
        responses={200: BannerResponseSerializer},
    )
    def get(self, request, banner_id):
        return success_response(data=BannerAdminSerializer(self.get_banner(banner_id)).data)

    @extend_schema(
        operation_id="admin_banners_update",
        request=BannerAdminSerializer,
        responses={200: BannerResponseSerializer},
    )
    def patch(self, request, banner_id):
        banner = self.get_banner(banner_id)
        serializer = BannerAdminSerializer(banner, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated = BannerService.update(
            banner=banner,
            data=dict(serializer.validated_data),
        )
        return success_response(
            message="Cập nhật banner thành công",
            data=BannerAdminSerializer(updated).data,
        )

    @extend_schema(
        operation_id="admin_banners_delete",
        responses={200: BannerDeleteResponseSerializer},
    )
    def delete(self, request, banner_id):
        deleted = BannerService.soft_delete(banner=self.get_banner(banner_id))
        return success_response(
            message="Xóa banner thành công",
            data={"id": str(deleted.pk), "is_deleted": True},
        )


class AdminBannerReorderView(APIView):
    permission_classes = [IsAdmin]

    @extend_schema(
        operation_id="admin_banners_reorder",
        request=BannerReorderSerializer,
        responses={200: BannerReorderResponseSerializer},
    )
    def post(self, request):
        serializer = BannerReorderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        banners = BannerService.reorder(**serializer.validated_data)
        return success_response(
            message="Sắp xếp banner thành công",
            data=BannerAdminSerializer(banners, many=True).data,
        )


class HomePageView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        operation_id="storefront_home",
        responses={200: HomeResponseSerializer},
    )
    def get(self, request):
        dynamic_prices = FlashSaleService.has_active_or_upcoming_sale()
        cached_data = None if dynamic_prices else safe_cache_get(HOME_PAGE_CACHE_KEY)
        if cached_data is not None:
            return success_response(
                message="Lấy nội dung trang chủ thành công",
                data=cached_data,
            )
        new_arrivals, best_sellers = get_home_products()
        data = {
            "banners": BannerPublicSerializer(get_active_banners(), many=True).data,
            "new_arrivals": PublicProductListSerializer(
                new_arrivals,
                many=True,
                context={"request": request},
            ).data,
            "best_sellers": PublicProductListSerializer(
                best_sellers,
                many=True,
                context={"request": request},
            ).data,
            "categories": CategoryTreeSerializer(
                get_home_categories(),
                many=True,
                context={"request": request},
            ).data,
        }
        if not dynamic_prices:
            safe_cache_set(
                HOME_PAGE_CACHE_KEY,
                data,
                timeout=HOME_PAGE_CACHE_TTL,
            )
        return success_response(
            message="Lấy nội dung trang chủ thành công",
            data=data,
        )
