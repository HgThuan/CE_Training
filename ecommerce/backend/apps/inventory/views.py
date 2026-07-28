from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.account.permissions import IsCustomer
from apps.common.exceptions import BusinessError
from apps.common.responses import success_response
from apps.product.models import ProductVariant

from .permissions import IsInventoryOwner, IsSeller
from .selectors import (
    get_inventory_for_shop,
    get_low_stock_variants,
    get_movement_history,
    get_shop_for_seller,
    get_stock_entries_for_shop,
    get_stock_out_entries_for_shop,
)
from .serializers import (
    InventoryBalanceResponseSerializer,
    InventoryBalanceSerializer,
    InventoryListResponseSerializer,
    MovementFilterSerializer,
    StockAlertResponseSerializer,
    StockAlertSerializer,
    StockEntryListResponseSerializer,
    StockEntryResponseSerializer,
    StockEntrySerializer,
    StockEntryUpdateSerializer,
    StockEntryWriteSerializer,
    StockMovementListResponseSerializer,
    StockMovementSerializer,
    StockOutEntryListResponseSerializer,
    StockOutEntryResponseSerializer,
    StockOutEntrySerializer,
    StockOutEntryUpdateSerializer,
    StockOutEntryWriteSerializer,
    ThresholdSerializer,
)
from .services import StockAlertService, StockService


class InventoryListView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated, IsSeller]
    serializer_class = InventoryBalanceSerializer

    @extend_schema(
        operation_id="seller_inventory_list",
        responses=InventoryListResponseSerializer,
    )
    def get(self, request):
        shop = get_shop_for_seller(request.user)
        low_stock = str(request.query_params.get("low_stock", "")).lower()
        queryset = (
            get_low_stock_variants(shop)
            if low_stock in {"1", "true", "yes"}
            else get_inventory_for_shop(shop)
        )
        page = self.paginate_queryset(queryset)
        return self.get_paginated_response(
            InventoryBalanceSerializer(page, many=True).data
        )


class StockMovementListView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated, IsSeller]
    serializer_class = StockMovementSerializer

    @extend_schema(
        operation_id="seller_inventory_movements",
        parameters=[MovementFilterSerializer],
        responses=StockMovementListResponseSerializer,
    )
    def get(self, request):
        filters = MovementFilterSerializer(data=request.query_params)
        filters.is_valid(raise_exception=True)
        shop = get_shop_for_seller(request.user)
        variant = None
        if variant_id := filters.validated_data.get("variant_id"):
            variant = ProductVariant.objects.filter(
                pk=variant_id,
                shop=shop,
                product__shop=shop,
                is_deleted=False,
            ).first()
            if variant is None:
                raise BusinessError("Không tìm thấy biến thể", http_status=404)
        queryset = get_movement_history(variant, shop)
        if date_from := filters.validated_data.get("date_from"):
            queryset = queryset.filter(created_at__gte=date_from)
        if date_to := filters.validated_data.get("date_to"):
            queryset = queryset.filter(created_at__lte=date_to)
        page = self.paginate_queryset(queryset)
        return self.get_paginated_response(
            StockMovementSerializer(page, many=True).data
        )


class StockEntryListCreateView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated, IsSeller]
    serializer_class = StockEntrySerializer

    @extend_schema(
        operation_id="seller_stock_entries_list",
        responses=StockEntryListResponseSerializer,
    )
    def get(self, request):
        shop = get_shop_for_seller(request.user)
        page = self.paginate_queryset(get_stock_entries_for_shop(shop))
        return self.get_paginated_response(StockEntrySerializer(page, many=True).data)

    @extend_schema(
        operation_id="seller_stock_entries_create",
        request=StockEntryWriteSerializer,
        responses=StockEntryResponseSerializer,
    )
    def post(self, request):
        serializer = StockEntryWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        entry = StockService.create_stock_entry(
            user=request.user,
            data=dict(serializer.validated_data),
        )
        entry = StockService._stock_entry_with_relations(entry.pk)
        return success_response(
            message="Tạo phiếu nhập kho thành công",
            data=StockEntrySerializer(entry).data,
            status_code=status.HTTP_201_CREATED,
        )


class StockEntryDetailView(APIView):
    permission_classes = [IsAuthenticated, IsSeller, IsInventoryOwner]

    @extend_schema(
        operation_id="seller_stock_entries_update",
        request=StockEntryUpdateSerializer,
        responses=StockEntryResponseSerializer,
    )
    def patch(self, request, entry_id):
        serializer = StockEntryUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        entry = StockService.update_stock_entry(
            stock_entry_id=entry_id,
            user=request.user,
            data=dict(serializer.validated_data),
        )
        self.check_object_permissions(request, entry)
        return success_response(
            message="Cập nhật phiếu nhập kho thành công",
            data=StockEntrySerializer(entry).data,
        )


class StockEntryConfirmView(APIView):
    permission_classes = [IsAuthenticated, IsSeller, IsInventoryOwner]

    @extend_schema(
        operation_id="seller_stock_entries_confirm",
        request=None,
        responses=StockEntryResponseSerializer,
    )
    def post(self, request, entry_id):
        entry = StockService.confirm_stock_entry(entry_id, request.user)
        self.check_object_permissions(request, entry)
        return success_response(
            message="Xác nhận phiếu nhập kho thành công",
            data=StockEntrySerializer(entry).data,
        )


class StockOutEntryListCreateView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated, IsSeller]
    serializer_class = StockOutEntrySerializer

    @extend_schema(
        operation_id="seller_stock_out_entries_list",
        responses=StockOutEntryListResponseSerializer,
    )
    def get(self, request):
        shop = get_shop_for_seller(request.user)
        page = self.paginate_queryset(get_stock_out_entries_for_shop(shop))
        return self.get_paginated_response(
            StockOutEntrySerializer(page, many=True).data
        )

    @extend_schema(
        operation_id="seller_stock_out_entries_create",
        request=StockOutEntryWriteSerializer,
        responses=StockOutEntryResponseSerializer,
    )
    def post(self, request):
        serializer = StockOutEntryWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        entry = StockService.create_stock_out_entry(
            user=request.user,
            data=dict(serializer.validated_data),
        )
        entry = StockService._stock_out_with_relations(entry.pk)
        return success_response(
            message="Tạo phiếu xuất/kiểm kê thành công",
            data=StockOutEntrySerializer(entry).data,
            status_code=status.HTTP_201_CREATED,
        )


class StockOutEntryDetailView(APIView):
    permission_classes = [IsAuthenticated, IsSeller, IsInventoryOwner]

    @extend_schema(
        operation_id="seller_stock_out_entries_update",
        request=StockOutEntryUpdateSerializer,
        responses=StockOutEntryResponseSerializer,
    )
    def patch(self, request, entry_id):
        shop = get_shop_for_seller(request.user)
        current = get_stock_out_entries_for_shop(shop).filter(pk=entry_id).first()
        if current is None:
            raise BusinessError("Không tìm thấy phiếu xuất/kiểm kê", http_status=404)
        serializer = StockOutEntryUpdateSerializer(
            data=request.data,
            context={"entry": current},
        )
        serializer.is_valid(raise_exception=True)
        entry = StockService.update_stock_out_entry(
            stock_out_entry_id=entry_id,
            user=request.user,
            data=dict(serializer.validated_data),
        )
        self.check_object_permissions(request, entry)
        return success_response(
            message="Cập nhật phiếu xuất/kiểm kê thành công",
            data=StockOutEntrySerializer(entry).data,
        )


class StockOutEntryConfirmView(APIView):
    permission_classes = [IsAuthenticated, IsSeller, IsInventoryOwner]

    @extend_schema(
        operation_id="seller_stock_out_entries_confirm",
        request=None,
        responses=StockOutEntryResponseSerializer,
    )
    def post(self, request, entry_id):
        entry = StockService.confirm_stock_out(entry_id, request.user)
        self.check_object_permissions(request, entry)
        return success_response(
            message="Xác nhận phiếu xuất/kiểm kê thành công",
            data=StockOutEntrySerializer(entry).data,
        )


class ThresholdUpdateView(APIView):
    permission_classes = [IsAuthenticated, IsSeller, IsInventoryOwner]

    @extend_schema(
        operation_id="seller_inventory_threshold_update",
        request=ThresholdSerializer,
        responses=InventoryBalanceResponseSerializer,
    )
    def post(self, request, variant_id):
        serializer = ThresholdSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        balance = StockService.update_threshold(
            variant_id=variant_id,
            user=request.user,
            low_stock_threshold=serializer.validated_data["low_stock_threshold"],
        )
        self.check_object_permissions(request, balance)
        return success_response(
            message="Cập nhật ngưỡng tồn kho thành công",
            data=InventoryBalanceSerializer(balance).data,
        )


class StockAlertCreateView(APIView):
    permission_classes = [IsAuthenticated, IsCustomer]

    @extend_schema(
        operation_id="customer_stock_waitlist_create",
        request=None,
        responses=StockAlertResponseSerializer,
    )
    def post(self, request, variant_id):
        alert = StockAlertService.register(
            variant_id=variant_id,
            user=request.user,
        )
        return success_response(
            message="Đã đăng ký báo khi sản phẩm có hàng",
            data=StockAlertSerializer(alert).data,
            status_code=status.HTTP_201_CREATED,
        )
