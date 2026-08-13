import uuid

from django.db.models import Count, F, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import OpenApiTypes, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.views import APIView

from apps.account.models import CustomerProfile, Shop
from apps.account.permissions import IsAdmin, IsCustomer, IsSeller
from apps.cart.services import CartService
from apps.common.exceptions import BusinessError
from apps.common.pagination import StandardPagination
from apps.common.responses import success_response
from apps.product.models import Product, ProductVariant
from apps.promotion.models import FlashSale, UserVoucher, Voucher
from apps.promotion.permissions import IsVoucherShopOwner
from apps.promotion.selectors import active_flash_sales, platform_vouchers, shop_vouchers
from apps.promotion.serializers import (
    CheckoutVoucherApplySerializer,
    CheckoutVoucherCodeSerializer,
    FlashSaleCatalogVariantSerializer,
    FlashSaleSerializer,
    UserVoucherSerializer,
    VoucherCenterSerializer,
    VoucherCollectSerializer,
    VoucherSerializer,
)
from apps.promotion.services import UserVoucherService


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


class VoucherCenterView(PaginatedAPIView):
    permission_classes = [AllowAny]

    def get(self, request: Request):
        now = timezone.now()
        customer = None
        if request.user.is_authenticated and request.user.role == "customer":
            customer = CustomerProfile.objects.filter(user=request.user).first()
        queryset = Voucher.objects.filter(
            is_active=True,
            collect_type=Voucher.CollectType.MANUAL,
            valid_from__lte=now,
            valid_until__gte=now,
        ).filter(Q(remaining_quantity__isnull=True) | Q(remaining_quantity__gt=0))
        if customer is not None:
            queryset = queryset.annotate(
                claimed_count=Count(
                    "user_vouchers",
                    filter=Q(user_vouchers__user=customer),
                )
            ).filter(claimed_count__lt=F("usage_limit_per_user"))
        queryset = queryset.select_related("shop", "applicable_category").order_by(
            "valid_until", "id"
        )
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request, view=self)
        data = VoucherCenterSerializer(
            page,
            many=True,
            context={"customer": customer},
        ).data
        return paginator.get_paginated_response(data)


class VoucherCollectView(APIView):
    permission_classes = [IsCustomer]

    def post(self, request: Request, campaign_id: uuid.UUID):
        serializer = VoucherCollectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        idempotency_key = request.headers.get("Idempotency-Key") or serializer.validated_data.get(
            "idempotency_key", ""
        )
        try:
            user_voucher, created = UserVoucherService.collect(
                campaign_id=campaign_id,
                user=request.user,
                idempotency_key=idempotency_key,
            )
        except Voucher.DoesNotExist as exc:
            raise BusinessError("Voucher không tồn tại", http_status=404) from exc
        return success_response(
            data=UserVoucherSerializer(user_voucher).data,
            message="Đã lưu voucher" if created else "Voucher đã được lưu trước đó",
            status_code=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class MyVoucherListView(PaginatedAPIView):
    permission_classes = [IsCustomer]

    def get(self, request: Request):
        customer = UserVoucherService.customer_for(request.user)
        UserVoucherService.release_expired_pending(customer=customer)
        queryset = UserVoucher.objects.filter(user=customer).select_related(
            "voucher_campaign__shop",
            "voucher_campaign__applicable_category",
        )
        requested_status = request.query_params.get("status")
        if requested_status:
            if requested_status not in UserVoucher.Status.values:
                raise BusinessError("Trạng thái voucher không hợp lệ")
            queryset = queryset.filter(status=requested_status)
        return self.paginate(request, queryset, UserVoucherSerializer)


def _selected_item_ids(request: Request) -> list[str] | None:
    raw = request.query_params.get("selected_item_ids", "").strip()
    return [value for value in raw.split(",") if value] or None


class CheckoutAvailableVoucherView(APIView):
    permission_classes = [IsCustomer]

    def get(self, request: Request):
        cart = CartService.get_or_create_customer_cart(request.user)
        evaluation = UserVoucherService.evaluate(
            cart=cart,
            selected_item_ids=_selected_item_ids(request),
        )
        results = []
        for entry in evaluation["results"]:
            data = UserVoucherSerializer(entry["user_voucher"]).data
            data.update(
                {
                    "is_eligible": entry["is_eligible"],
                    "reason": entry["reason"],
                    "estimated_discount": entry["estimated_discount"],
                }
            )
            results.append(data)
        return success_response(
            data={
                "results": results,
                "best_voucher_id": (
                    str(evaluation["best_voucher_id"])
                    if evaluation["best_voucher_id"] is not None
                    else None
                ),
            },
            message="Lấy voucher phù hợp thành công",
        )


class CheckoutApplyVoucherView(APIView):
    permission_classes = [IsCustomer]

    def post(self, request: Request):
        serializer = CheckoutVoucherApplySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        cart = CartService.get_or_create_customer_cart(request.user)
        result = UserVoucherService.apply(
            cart=cart,
            **serializer.validated_data,
        )
        return success_response(data=result, message="Đã khóa voucher và tính lại đơn hàng")


class CheckoutApplyVoucherByCodeView(APIView):
    permission_classes = [IsCustomer]

    def post(self, request: Request):
        serializer = CheckoutVoucherCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data
        campaign = get_object_or_404(Voucher, code__iexact=payload["code"].strip())
        user_voucher, _ = UserVoucherService.collect(
            campaign_id=campaign.pk,
            user=request.user,
            idempotency_key=payload["idempotency_key"],
        )
        cart = CartService.get_or_create_customer_cart(request.user)
        result = UserVoucherService.apply(
            cart=cart,
            user_voucher_ids=[user_voucher.pk],
            checkout_token=payload.get("checkout_token"),
            selected_item_ids=payload.get("selected_item_ids"),
        )
        return success_response(data=result, message="Đã áp dụng mã voucher riêng tư")


class ShopVoucherListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request: Request, shop_id: int):
        now = timezone.now()
        customer = None
        if request.user.is_authenticated and request.user.role == "customer":
            customer = CustomerProfile.objects.filter(user=request.user).first()
        queryset = Voucher.objects.filter(
            scope=Voucher.Scope.SHOP,
            shop_id=shop_id,
            is_active=True,
            valid_from__lte=now,
            valid_until__gte=now,
        ).filter(Q(remaining_quantity__isnull=True) | Q(remaining_quantity__gt=0))
        return success_response(
            data=VoucherCenterSerializer(
                queryset,
                many=True,
                context={"customer": customer},
            ).data,
            message="Lấy voucher của shop thành công",
        )


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


class AdminFlashSaleCatalogView(PaginatedAPIView):
    """Human-readable catalog used by admins when composing a Flash Sale."""

    permission_classes = [IsAdmin]

    def get(self, request: Request):
        queryset = (
            ProductVariant.objects.select_related(
                "product__category",
                "shop",
                "inventory_balance",
            )
            .prefetch_related("product__media")
            .filter(
                product__status=Product.Status.APPROVED,
                product__is_deleted=False,
                product__category__is_active=True,
                product__category__is_deleted=False,
                shop__status=Shop.Status.APPROVED,
                is_active=True,
                is_deleted=False,
            )
            .filter(
                Q(inventory_balance__available_stock__gt=0)
                | Q(inventory_balance__isnull=True, stock_quantity__gt=0)
            )
            .order_by("product__name", "sku", "id")
        )
        category_id = request.query_params.get("category_id")
        if category_id:
            queryset = queryset.filter(product__category_id=category_id)
        search = request.query_params.get("search", "").strip()
        if search:
            queryset = queryset.filter(
                Q(product__name__icontains=search)
                | Q(sku__icontains=search)
                | Q(name__icontains=search)
                | Q(shop__name__icontains=search)
            )
        return self.paginate(request, queryset, FlashSaleCatalogVariantSerializer)


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
