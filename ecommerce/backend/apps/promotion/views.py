import uuid

from django.db.models import Count, F, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import OpenApiTypes, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.views import APIView

from apps.account.models import Shop
from apps.account.permissions import IsAdmin, IsCustomer, IsSeller
from apps.common.pagination import StandardPagination
from apps.common.responses import success_response
from apps.promotion.models import FlashSale, Voucher
from apps.promotion.permissions import IsVoucherShopOwner
from apps.promotion.selectors import active_flash_sales, platform_vouchers, shop_vouchers
from apps.promotion.serializers import FlashSaleSerializer, VoucherSerializer


class PaginatedAPIView(APIView):
    pagination_class = StandardPagination

    def paginate(self, request: Request, queryset, serializer_class):
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request, view=self)
        return paginator.get_paginated_response(serializer_class(page, many=True).data)


class AdminVoucherListCreateView(PaginatedAPIView):
    permission_classes = [IsAdmin]

    def get(self, request: Request):
        return self.paginate(request, platform_vouchers(), VoucherSerializer)

    @extend_schema(request=VoucherSerializer, responses={201: VoucherSerializer})
    def post(self, request: Request):
        data = request.data.copy()
        data["scope"] = Voucher.Scope.PLATFORM
        data["shop"] = None
        serializer = VoucherSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        voucher = serializer.save(scope=Voucher.Scope.PLATFORM, shop=None)
        return success_response(
            data=VoucherSerializer(voucher).data,
            message="Tạo voucher sàn thành công",
            status_code=status.HTTP_201_CREATED,
        )


class AdminVoucherDetailView(APIView):
    permission_classes = [IsAdmin]

    def _object(self, pk: uuid.UUID):
        return get_object_or_404(platform_vouchers(), pk=pk)

    def get(self, request: Request, pk: uuid.UUID):
        return success_response(data=VoucherSerializer(self._object(pk)).data)

    def patch(self, request: Request, pk: uuid.UUID):
        voucher = self._object(pk)
        serializer = VoucherSerializer(voucher, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save(scope=Voucher.Scope.PLATFORM, shop=None)
        return success_response(data=serializer.data, message="Cập nhật voucher sàn thành công")

    def delete(self, request: Request, pk: uuid.UUID):
        self._object(pk).delete()
        return success_response(data=None, message="Đã xóa voucher sàn")


class SellerVoucherListCreateView(PaginatedAPIView):
    permission_classes = [IsSeller]

    @staticmethod
    def shop(request: Request) -> Shop:
        return get_object_or_404(Shop, owner=request.user, is_deleted=False)

    def get(self, request: Request):
        return self.paginate(request, shop_vouchers(self.shop(request)), VoucherSerializer)

    @extend_schema(request=VoucherSerializer, responses={201: VoucherSerializer})
    def post(self, request: Request):
        shop = self.shop(request)
        data = request.data.copy()
        data["scope"] = Voucher.Scope.SHOP
        data["shop"] = shop.pk
        serializer = VoucherSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        voucher = serializer.save(scope=Voucher.Scope.SHOP, shop=shop)
        return success_response(
            data=VoucherSerializer(voucher).data,
            message="Tạo voucher shop thành công",
            status_code=status.HTTP_201_CREATED,
        )


class SellerVoucherDetailView(APIView):
    permission_classes = [IsSeller, IsVoucherShopOwner]

    def _object(self, request: Request, pk: uuid.UUID) -> Voucher:
        voucher = get_object_or_404(Voucher.objects.select_related("shop"), pk=pk)
        self.check_object_permissions(request, voucher)
        return voucher

    def get(self, request: Request, pk: uuid.UUID):
        return success_response(data=VoucherSerializer(self._object(request, pk)).data)

    def patch(self, request: Request, pk: uuid.UUID):
        voucher = self._object(request, pk)
        data = request.data.copy()
        data.pop("scope", None)
        data.pop("shop", None)
        serializer = VoucherSerializer(voucher, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save(scope=Voucher.Scope.SHOP, shop=voucher.shop)
        return success_response(data=serializer.data, message="Cập nhật voucher shop thành công")

    def delete(self, request: Request, pk: uuid.UUID):
        self._object(request, pk).delete()
        return success_response(data=None, message="Đã xóa voucher shop")


class AvailableVoucherListView(PaginatedAPIView):
    permission_classes = [IsCustomer]

    def get(self, request: Request):
        now = timezone.now()
        queryset = (
            Voucher.objects.filter(
                is_active=True,
                valid_from__lte=now,
                valid_until__gte=now,
            )
            .annotate(usage_count=Count("usages"))
            .filter(Q(total_usage_limit__isnull=True) | Q(usage_count__lt=F("total_usage_limit")))
            .select_related("shop", "applicable_category")
            .order_by("valid_until")
        )
        return self.paginate(request, queryset, VoucherSerializer)


class AdminFlashSaleListCreateView(PaginatedAPIView):
    permission_classes = [IsAdmin]

    def get(self, request: Request):
        queryset = FlashSale.objects.prefetch_related(
            "items__variant__product__shop",
            "items__variant__product__media",
        )
        return self.paginate(request, queryset, FlashSaleSerializer)

    @extend_schema(request=FlashSaleSerializer, responses={201: FlashSaleSerializer})
    def post(self, request: Request):
        serializer = FlashSaleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        flash_sale = serializer.save()
        flash_sale = FlashSale.objects.prefetch_related(
            "items__variant__product__shop",
            "items__variant__product__media",
        ).get(pk=flash_sale.pk)
        return success_response(
            data=FlashSaleSerializer(flash_sale).data,
            message="Tạo Flash Sale thành công",
            status_code=status.HTTP_201_CREATED,
        )


class AdminFlashSaleDetailView(APIView):
    permission_classes = [IsAdmin]

    @staticmethod
    def _object(pk: uuid.UUID):
        return get_object_or_404(
            FlashSale.objects.prefetch_related(
                "items__variant__product__shop",
                "items__variant__product__media",
            ),
            pk=pk,
        )

    def get(self, request: Request, pk: uuid.UUID):
        return success_response(data=FlashSaleSerializer(self._object(pk)).data)

    def patch(self, request: Request, pk: uuid.UUID):
        serializer = FlashSaleSerializer(self._object(pk), data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        flash_sale = serializer.save()
        return success_response(
            data=FlashSaleSerializer(self._object(flash_sale.pk)).data,
            message="Cập nhật Flash Sale thành công",
        )

    def delete(self, request: Request, pk: uuid.UUID):
        self._object(pk).delete()
        return success_response(data=None, message="Đã xóa Flash Sale")


class ActiveFlashSaleListView(PaginatedAPIView):
    permission_classes = [AllowAny]

    @extend_schema(responses={200: OpenApiTypes.OBJECT})
    def get(self, request: Request):
        return self.paginate(request, active_flash_sales(), FlashSaleSerializer)
