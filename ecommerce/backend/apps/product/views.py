from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from apps.account.permissions import IsAdmin, IsSeller
from apps.common.cache_utils import (
    PRODUCT_DETAIL_CACHE_TTL,
    SEARCH_RESULTS_CACHE_TTL,
    SEARCH_SUGGESTIONS_CACHE_TTL,
    product_detail_cache_key,
    safe_cache_get,
    safe_cache_set,
    search_results_cache_key,
    search_suggestions_cache_key,
)
from apps.common.exceptions import BusinessError
from apps.common.responses import success_response
from apps.promotion.services import FlashSaleService

from .permissions import IsShopOwner
from .selectors import ProductSelector, SearchSelector
from .serializers import (
    AdminProductFilterSerializer,
    AdminProductHideSerializer,
    AdminProductListResponseSerializer,
    AdminProductListSerializer,
    AdminProductRejectSerializer,
    AdminProductResponseSerializer,
    AttributeCreateSerializer,
    AttributeListResponseSerializer,
    AttributeListSerializer,
    AttributeResponseSerializer,
    MediaReorderSerializer,
    MediaResponseSerializer,
    MediaUploadSerializer,
    ProductDeleteResponseSerializer,
    ProductMediaSerializer,
    PublicProductDetailSerializer,
    PublicProductFilterSerializer,
    PublicProductListResponseSerializer,
    PublicProductListSerializer,
    PublicProductResponseSerializer,
    SearchFilterSerializer,
    SearchSuggestionListResponseSerializer,
    SearchSuggestionQuerySerializer,
    SearchSuggestionSerializer,
    SellerProductCreateSerializer,
    SellerProductDetailSerializer,
    SellerProductFilterSerializer,
    SellerProductListResponseSerializer,
    SellerProductListSerializer,
    SellerProductResponseSerializer,
    SellerProductUpdateSerializer,
    SellerProductVariantSerializer,
    VariantGenerateSerializer,
    VariantListResponseSerializer,
    VariantLookupSerializer,
    VariantResponseSerializer,
    VariantUpdateSerializer,
)
from .services import AttributeService, MediaService, ProductService, VariantService


def _request_id(request) -> str:
    return getattr(request, "request_id", "")


class SellerProductViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated, IsSeller, IsShopOwner]
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    serializer_class = SellerProductDetailSerializer
    lookup_url_kwarg = "product_id"

    def get_queryset(self):
        return ProductSelector.for_seller(self.request.user)

    def get_serializer_class(self):
        serializer_by_action = {
            "create": SellerProductCreateSerializer,
            "partial_update": SellerProductUpdateSerializer,
            "list": SellerProductListSerializer,
            "upload_media": MediaUploadSerializer,
            "reorder_media": MediaReorderSerializer,
            "create_attribute": AttributeCreateSerializer,
            "generate_variants": VariantGenerateSerializer,
            "lookup_variant": VariantLookupSerializer,
            "update_variant": VariantUpdateSerializer,
        }
        return serializer_by_action.get(
            getattr(self, "action", ""),
            SellerProductDetailSerializer,
        )

    @extend_schema(
        operation_id="seller_products_list",
        parameters=[SellerProductFilterSerializer],
        responses={200: SellerProductListResponseSerializer},
    )
    def list(self, request):
        filters = SellerProductFilterSerializer(data=request.query_params)
        filters.is_valid(raise_exception=True)
        queryset = ProductSelector.filter_for_seller(
            self.get_queryset(),
            filters.validated_data,
        )
        page = self.paginate_queryset(queryset)
        return self.get_paginated_response(
            SellerProductListSerializer(
                page,
                many=True,
                context=self.get_serializer_context(),
            ).data
        )

    @extend_schema(
        operation_id="seller_products_create",
        request=SellerProductCreateSerializer,
        responses={201: SellerProductResponseSerializer},
    )
    def create(self, request):
        serializer = SellerProductCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product = ProductService.create_product(
            seller_user=request.user,
            data=dict(serializer.validated_data),
        )
        return success_response(
            message="Tạo sản phẩm nháp thành công",
            data=SellerProductDetailSerializer(
                product,
                context=self.get_serializer_context(),
            ).data,
            status_code=status.HTTP_201_CREATED,
        )

    @extend_schema(
        operation_id="seller_products_retrieve",
        responses={200: SellerProductResponseSerializer},
    )
    def retrieve(self, request, product_id=None):
        product = self.get_object()
        return success_response(
            message="Lấy chi tiết sản phẩm thành công",
            data=SellerProductDetailSerializer(
                product,
                context=self.get_serializer_context(),
            ).data,
        )

    @extend_schema(
        operation_id="seller_products_update",
        request=SellerProductUpdateSerializer,
        responses={200: SellerProductResponseSerializer},
    )
    def partial_update(self, request, product_id=None):
        product = self.get_object()
        serializer = SellerProductUpdateSerializer(
            product,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        product = ProductService.update_product(
            product=product,
            seller_user=request.user,
            data=dict(serializer.validated_data),
            request_id=_request_id(request),
        )
        return success_response(
            message="Cập nhật sản phẩm thành công",
            data=SellerProductDetailSerializer(
                product,
                context=self.get_serializer_context(),
            ).data,
        )

    @extend_schema(
        operation_id="seller_products_delete",
        responses={200: ProductDeleteResponseSerializer},
    )
    def destroy(self, request, product_id=None):
        product = ProductService.soft_delete_product(
            product=self.get_object(),
            seller_user=request.user,
        )
        return success_response(
            message="Xóa sản phẩm thành công",
            data={"id": str(product.pk), "is_deleted": True},
        )

    @extend_schema(
        operation_id="seller_products_submit",
        request=None,
        responses={200: SellerProductResponseSerializer},
    )
    @action(detail=True, methods=["post"])
    def submit(self, request, product_id=None):
        product = ProductService.submit_for_review(
            product=self.get_object(),
            actor=request.user,
            request_id=_request_id(request),
        )
        return success_response(
            message="Đã gửi sản phẩm chờ duyệt",
            data=SellerProductDetailSerializer(
                product,
                context=self.get_serializer_context(),
            ).data,
        )

    @extend_schema(
        operation_id="seller_products_suspend",
        request=None,
        responses={200: SellerProductResponseSerializer},
    )
    @action(detail=True, methods=["post"])
    def suspend(self, request, product_id=None):
        product = ProductService.suspend_product(
            product=self.get_object(),
            seller_user=request.user,
            request_id=_request_id(request),
        )
        return success_response(
            message="Đã tạm ngưng bán sản phẩm",
            data=SellerProductDetailSerializer(
                product,
                context=self.get_serializer_context(),
            ).data,
        )

    @extend_schema(
        operation_id="seller_products_restore",
        request=None,
        responses={200: SellerProductResponseSerializer},
    )
    @action(detail=True, methods=["post"])
    def restore(self, request, product_id=None):
        product = ProductService.restore_product(
            product=self.get_object(),
            seller_user=request.user,
            request_id=_request_id(request),
        )
        return success_response(
            message="Đã mở bán lại sản phẩm",
            data=SellerProductDetailSerializer(
                product,
                context=self.get_serializer_context(),
            ).data,
        )

    @extend_schema(
        operation_id="seller_products_media_upload",
        request=MediaUploadSerializer,
        responses={201: MediaResponseSerializer},
    )
    @action(detail=True, methods=["post"])
    def upload_media(self, request, product_id=None):
        product = self.get_object()
        serializer = MediaUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        media = MediaService.upload_media(
            product=product,
            uploaded_file=serializer.validated_data["file"],
            media_type=serializer.validated_data["media_type"],
            seller_user=request.user,
            variant_id=serializer.validated_data.get("variant_id"),
        )
        return success_response(
            message="Tải media sản phẩm thành công",
            data=ProductMediaSerializer(media).data,
            status_code=status.HTTP_201_CREATED,
        )

    @extend_schema(
        operation_id="seller_products_media_delete",
        responses={200: ProductDeleteResponseSerializer},
    )
    @action(detail=True, methods=["delete"])
    def delete_media(self, request, product_id=None, media_id=None):
        product = self.get_object()
        media = ProductSelector.media_for_product(
            product=product,
            media_id=media_id,
        )
        if media is None:
            raise BusinessError("Không tìm thấy media", http_status=404)
        self.check_object_permissions(request, media)
        MediaService.delete_media(media=media, seller_user=request.user)
        return success_response(
            message="Xóa media thành công",
            data={"id": str(media_id), "is_deleted": True},
        )

    @extend_schema(
        operation_id="seller_products_media_reorder",
        request=MediaReorderSerializer,
        responses={200: SellerProductResponseSerializer},
    )
    @action(detail=True, methods=["post"])
    def reorder_media(self, request, product_id=None):
        product = self.get_object()
        serializer = MediaReorderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        MediaService.reorder_media(
            product=product,
            ordered_ids=serializer.validated_data["ordered_ids"],
            seller_user=request.user,
        )
        product = self.get_object()
        return success_response(
            message="Sắp xếp media thành công",
            data=SellerProductDetailSerializer(
                product,
                context=self.get_serializer_context(),
            ).data,
        )

    @extend_schema(
        operation_id="seller_attributes_list",
        responses={200: AttributeListResponseSerializer},
    )
    @action(detail=False, methods=["get"])
    def list_attributes(self, request):
        attributes = ProductSelector.attributes_for_seller(request.user)
        page = self.paginate_queryset(attributes)
        return self.get_paginated_response(AttributeListSerializer(page, many=True).data)

    @extend_schema(
        operation_id="seller_attributes_create",
        request=AttributeCreateSerializer,
        responses={201: AttributeResponseSerializer},
    )
    @action(detail=False, methods=["post"])
    def create_attribute(self, request):
        serializer = AttributeCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        attribute = AttributeService.create_attribute(
            seller_user=request.user,
            data=dict(serializer.validated_data),
        )
        return success_response(
            message="Tạo thuộc tính và giá trị thành công",
            data=AttributeListSerializer(attribute).data,
            status_code=status.HTTP_201_CREATED,
        )

    @extend_schema(
        operation_id="seller_products_variants_generate",
        request=VariantGenerateSerializer,
        responses={201: VariantListResponseSerializer},
    )
    @action(detail=True, methods=["post"])
    def generate_variants(self, request, product_id=None):
        product = self.get_object()
        serializer = VariantGenerateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        created = VariantService.generate_variants(
            product=product,
            attribute_value_ids=serializer.validated_data["attribute_value_ids"],
            seller_user=request.user,
        )
        variants = ProductSelector.variants_for_product(
            product=product,
            variant_ids=[variant.pk for variant in created],
        )
        return success_response(
            message="Tạo tổ hợp biến thể thành công",
            data=SellerProductVariantSerializer(variants, many=True).data,
            status_code=status.HTTP_201_CREATED,
        )

    @extend_schema(
        operation_id="seller_variants_lookup_by_barcode",
        parameters=[VariantLookupSerializer],
        responses={200: VariantResponseSerializer},
    )
    @action(detail=False, methods=["get"])
    def lookup_variant(self, request):
        serializer = VariantLookupSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        variant = ProductSelector.variant_by_barcode(
            seller_user=request.user,
            barcode=serializer.validated_data["barcode"],
        )
        if variant is None:
            raise BusinessError("Không tìm thấy biến thể theo barcode", http_status=404)
        return success_response(
            message="Tìm thấy biến thể",
            data=SellerProductVariantSerializer(variant).data,
        )

    @extend_schema(
        operation_id="seller_products_variants_update",
        request=VariantUpdateSerializer,
        responses={200: VariantResponseSerializer},
    )
    @action(detail=True, methods=["patch"])
    def update_variant(
        self,
        request,
        product_id=None,
        variant_id=None,
    ):
        product = self.get_object()
        variant = ProductSelector.variant_for_product(
            product=product,
            variant_id=variant_id,
        )
        if variant is None:
            raise BusinessError("Không tìm thấy biến thể", http_status=404)
        self.check_object_permissions(request, variant)
        serializer = VariantUpdateSerializer(
            variant,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        variant = VariantService.update_variant(
            variant=variant,
            seller_user=request.user,
            data=dict(serializer.validated_data),
        )
        return success_response(
            message="Cập nhật biến thể thành công",
            data=SellerProductVariantSerializer(variant).data,
        )


class AdminProductViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated, IsAdmin]
    serializer_class = AdminProductListSerializer
    lookup_url_kwarg = "product_id"

    def get_queryset(self):
        return ProductSelector.admin_all({"is_deleted": False})

    @extend_schema(
        operation_id="admin_products_list",
        parameters=[AdminProductFilterSerializer],
        responses={200: AdminProductListResponseSerializer},
    )
    def list(self, request):
        filters = AdminProductFilterSerializer(data=request.query_params)
        filters.is_valid(raise_exception=True)
        queryset = ProductSelector.filter_for_admin(
            self.get_queryset(),
            filters.validated_data,
        )
        page = self.paginate_queryset(queryset)
        return self.get_paginated_response(
            AdminProductListSerializer(
                page,
                many=True,
                context=self.get_serializer_context(),
            ).data
        )

    @extend_schema(
        operation_id="admin_products_pending",
        responses={200: AdminProductListResponseSerializer},
    )
    @action(detail=False, methods=["get"])
    def list_pending(self, request):
        page = self.paginate_queryset(ProductSelector.admin_pending())
        return self.get_paginated_response(
            AdminProductListSerializer(
                page,
                many=True,
                context=self.get_serializer_context(),
            ).data
        )

    @extend_schema(
        operation_id="admin_products_approve",
        request=None,
        responses={200: AdminProductResponseSerializer},
    )
    @action(detail=True, methods=["post"])
    def approve(self, request, product_id=None):
        product = ProductService.admin_approve(
            product=self.get_object(),
            admin_user=request.user,
            request_id=_request_id(request),
        )
        return success_response(
            message="Duyệt sản phẩm thành công",
            data=AdminProductListSerializer(product).data,
        )

    @extend_schema(
        operation_id="admin_products_reject",
        request=AdminProductRejectSerializer,
        responses={200: AdminProductResponseSerializer},
    )
    @action(detail=True, methods=["post"])
    def reject(self, request, product_id=None):
        serializer = AdminProductRejectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product = ProductService.admin_reject(
            product=self.get_object(),
            admin_user=request.user,
            reason=serializer.validated_data["rejection_reason"],
            request_id=_request_id(request),
        )
        return success_response(
            message="Từ chối sản phẩm thành công",
            data=AdminProductListSerializer(product).data,
        )

    @extend_schema(
        operation_id="admin_products_hide",
        request=AdminProductHideSerializer,
        responses={200: AdminProductResponseSerializer},
    )
    @action(detail=True, methods=["post"])
    def hide(self, request, product_id=None):
        serializer = AdminProductHideSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product = ProductService.admin_hide(
            product=self.get_object(),
            admin_user=request.user,
            reason=serializer.validated_data["reason"],
            request_id=_request_id(request),
        )
        return success_response(
            message="Ẩn sản phẩm thành công",
            data=AdminProductListSerializer(product).data,
        )

    @extend_schema(
        operation_id="admin_products_unhide",
        request=None,
        responses={200: AdminProductResponseSerializer},
    )
    @action(detail=True, methods=["post"])
    def unhide(self, request, product_id=None):
        product = ProductService.admin_unhide(
            product=self.get_object(),
            admin_user=request.user,
            request_id=_request_id(request),
        )
        return success_response(
            message="Bỏ ẩn sản phẩm thành công",
            data=AdminProductListSerializer(product).data,
        )

    @extend_schema(
        operation_id="admin_products_delete",
        responses={200: ProductDeleteResponseSerializer},
    )
    def destroy(self, request, product_id=None):
        product = ProductService.admin_soft_delete(
            product=self.get_object(),
            admin_user=request.user,
            request_id=_request_id(request),
        )
        return success_response(
            message="Xóa sản phẩm thành công",
            data={"id": str(product.pk), "is_deleted": True},
        )


class SearchView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = PublicProductListSerializer

    @extend_schema(
        operation_id="public_product_search",
        parameters=[SearchFilterSerializer],
        responses={200: PublicProductListResponseSerializer},
    )
    def get(self, request):
        filters = SearchFilterSerializer(data=request.query_params)
        filters.is_valid(raise_exception=True)
        cache_key = search_results_cache_key(filters.validated_data)
        dynamic_prices = FlashSaleService.has_active_or_upcoming_sale()
        cached_payload = None if dynamic_prices else safe_cache_get(cache_key)
        if cached_payload is not None:
            return Response(cached_payload)

        page = self.paginate_queryset(SearchSelector.search(filters.validated_data))
        data = PublicProductListSerializer(
            page,
            many=True,
            context=self.get_serializer_context(),
        ).data
        response = self.get_paginated_response(data)
        if not dynamic_prices:
            safe_cache_set(
                cache_key,
                response.data,
                timeout=SEARCH_RESULTS_CACHE_TTL,
            )
        return response


class SearchSuggestionView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = SearchSuggestionQuerySerializer

    @extend_schema(
        operation_id="public_product_search_suggestions",
        parameters=[SearchSuggestionQuerySerializer],
        responses={200: SearchSuggestionListResponseSerializer},
    )
    def get(self, request):
        query = self.get_serializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        query_text = query.validated_data["q"]
        limit = query.validated_data["limit"]
        cache_key = search_suggestions_cache_key(query_text)
        cached_suggestions = safe_cache_get(cache_key)
        if cached_suggestions is None:
            cached_suggestions = SearchSuggestionSerializer(
                SearchSelector.suggestions(query=query_text, limit=10),
                many=True,
            ).data
            safe_cache_set(
                cache_key,
                cached_suggestions,
                timeout=SEARCH_SUGGESTIONS_CACHE_TTL,
            )
        return success_response(
            message="Lấy gợi ý tìm kiếm thành công",
            data=list(cached_suggestions[:limit]),
        )


class PublicProductViewSet(viewsets.GenericViewSet):
    permission_classes = [AllowAny]
    serializer_class = PublicProductDetailSerializer

    def get_queryset(self):
        return ProductSelector.public_queryset()

    @extend_schema(
        operation_id="public_products_list",
        parameters=[PublicProductFilterSerializer],
        responses={200: PublicProductListResponseSerializer},
    )
    def list(self, request):
        filters = PublicProductFilterSerializer(data=request.query_params)
        filters.is_valid(raise_exception=True)
        queryset = ProductSelector.filter_public(
            self.get_queryset(),
            filters.validated_data,
        )
        page = self.paginate_queryset(queryset)
        return self.get_paginated_response(
            PublicProductListSerializer(
                page,
                many=True,
                context=self.get_serializer_context(),
            ).data
        )

    @extend_schema(
        operation_id="public_products_retrieve",
        parameters=[
            OpenApiParameter(
                name="shop_slug",
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Bắt buộc khi nhiều shop có cùng product slug.",
            )
        ],
        responses={200: PublicProductResponseSerializer},
    )
    def retrieve(self, request, slug=None):
        shop_slug = request.query_params.get("shop_slug")
        cache_key = product_detail_cache_key(
            slug=slug,
            shop_slug=shop_slug,
        )
        dynamic_prices = FlashSaleService.has_active_or_upcoming_sale()
        cached_data = None if dynamic_prices else safe_cache_get(cache_key)
        if cached_data is not None:
            return success_response(
                message="Lấy chi tiết sản phẩm thành công",
                data=cached_data,
            )

        product = ProductSelector.public_detail(
            slug=slug,
            shop_slug=shop_slug,
        )
        if product is None:
            raise BusinessError("Không tìm thấy sản phẩm", http_status=404)
        data = PublicProductDetailSerializer(
            product,
            context=self.get_serializer_context(),
        ).data
        if not dynamic_prices:
            safe_cache_set(
                cache_key,
                data,
                timeout=PRODUCT_DETAIL_CACHE_TTL,
            )
        return success_response(
            message="Lấy chi tiết sản phẩm thành công",
            data=data,
        )
