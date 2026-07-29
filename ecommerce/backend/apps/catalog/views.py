from drf_spectacular.utils import extend_schema
from rest_framework import generics
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from apps.account.permissions import IsAdmin
from apps.common.cache_utils import (
    CATEGORY_TREE_CACHE_KEY,
    CATEGORY_TREE_CACHE_TTL,
    safe_cache_get,
    safe_cache_set,
)
from apps.common.exceptions import BusinessError
from apps.common.responses import success_response

from .selectors import BrandSelector, CategorySelector
from .serializers import (
    BrandCreateSerializer,
    BrandListResponseSerializer,
    BrandListSerializer,
    BrandResponseSerializer,
    BrandUpdateSerializer,
    CategoryCreateSerializer,
    CategoryListResponseSerializer,
    CategoryReorderResponseSerializer,
    CategoryReorderSerializer,
    CategoryResponseSerializer,
    CategoryTreeResponseSerializer,
    CategoryTreeSerializer,
    CategoryUpdateSerializer,
    DeleteResponseSerializer,
)
from .services import BrandService, CategoryService


class PublicCategoryTreeView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        operation_id="public_categories_tree",
        responses={200: CategoryTreeResponseSerializer},
    )
    def get(self, request):
        cached_data = safe_cache_get(CATEGORY_TREE_CACHE_KEY)
        if cached_data is not None:
            return success_response(
                message="Lấy cây danh mục thành công",
                data=cached_data,
            )
        categories = CategorySelector.public_tree()
        data = CategoryTreeSerializer(categories, many=True).data
        safe_cache_set(
            CATEGORY_TREE_CACHE_KEY,
            data,
            timeout=CATEGORY_TREE_CACHE_TTL,
        )
        return success_response(
            message="Lấy cây danh mục thành công",
            data=data,
        )


class PublicBrandListView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = BrandListSerializer

    @extend_schema(
        operation_id="public_brands_list",
        responses={200: BrandListResponseSerializer},
    )
    def get(self, request):
        page = self.paginate_queryset(BrandSelector.public_list())
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)


class AdminCategoryListCreateView(generics.GenericAPIView):
    permission_classes = [IsAdmin]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return CategoryCreateSerializer
        return CategoryTreeSerializer

    @extend_schema(
        operation_id="admin_categories_list",
        responses={200: CategoryListResponseSerializer},
    )
    def get(self, request):
        page = self.paginate_queryset(CategorySelector.admin_list())
        return self.get_paginated_response(CategoryTreeSerializer(page, many=True).data)

    @extend_schema(
        operation_id="admin_categories_create",
        request=CategoryCreateSerializer,
        responses={201: CategoryResponseSerializer},
    )
    def post(self, request):
        serializer = CategoryCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        category = CategoryService.create(**serializer.validated_data)
        return success_response(
            message="Tạo danh mục thành công",
            data=CategoryTreeSerializer(category).data,
            status_code=201,
        )


class AdminCategoryDetailView(APIView):
    permission_classes = [IsAdmin]

    @staticmethod
    def get_category(category_id):
        category = CategorySelector.get_for_admin(category_id)
        if category is None:
            raise BusinessError("Không tìm thấy danh mục", http_status=404)
        return category

    @extend_schema(
        operation_id="admin_categories_retrieve",
        responses={200: CategoryResponseSerializer},
    )
    def get(self, request, category_id):
        return success_response(data=CategoryTreeSerializer(self.get_category(category_id)).data)

    @extend_schema(
        operation_id="admin_categories_update",
        request=CategoryUpdateSerializer,
        responses={200: CategoryResponseSerializer},
    )
    def patch(self, request, category_id):
        category = self.get_category(category_id)
        serializer = CategoryUpdateSerializer(
            category,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        category = CategoryService.update(
            category=category,
            data=dict(serializer.validated_data),
        )
        return success_response(
            message="Cập nhật danh mục thành công",
            data=CategoryTreeSerializer(category).data,
        )

    @extend_schema(
        operation_id="admin_categories_delete",
        responses={200: DeleteResponseSerializer},
    )
    def delete(self, request, category_id):
        category = CategoryService.soft_delete(category=self.get_category(category_id))
        return success_response(
            message="Xóa danh mục thành công",
            data={"id": str(category.pk), "is_deleted": True},
        )


class AdminCategoryReorderView(APIView):
    permission_classes = [IsAdmin]

    @extend_schema(
        operation_id="admin_categories_reorder",
        request=CategoryReorderSerializer,
        responses={200: CategoryReorderResponseSerializer},
    )
    def post(self, request):
        serializer = CategoryReorderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        categories = CategoryService.reorder(items=serializer.validated_data["items"])
        return success_response(
            message="Sắp xếp danh mục thành công",
            data=CategoryTreeSerializer(categories, many=True).data,
        )


class AdminBrandListCreateView(generics.GenericAPIView):
    permission_classes = [IsAdmin]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return BrandCreateSerializer
        return BrandListSerializer

    @extend_schema(
        operation_id="admin_brands_list",
        responses={200: BrandListResponseSerializer},
    )
    def get(self, request):
        page = self.paginate_queryset(BrandSelector.admin_list())
        return self.get_paginated_response(BrandListSerializer(page, many=True).data)

    @extend_schema(
        operation_id="admin_brands_create",
        request=BrandCreateSerializer,
        responses={201: BrandResponseSerializer},
    )
    def post(self, request):
        serializer = BrandCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        brand = BrandService.create(**serializer.validated_data)
        return success_response(
            message="Tạo thương hiệu thành công",
            data=BrandListSerializer(brand).data,
            status_code=201,
        )


class AdminBrandDetailView(APIView):
    permission_classes = [IsAdmin]

    @staticmethod
    def get_brand(brand_id):
        brand = BrandSelector.get_for_admin(brand_id)
        if brand is None:
            raise BusinessError("Không tìm thấy thương hiệu", http_status=404)
        return brand

    @extend_schema(
        operation_id="admin_brands_retrieve",
        responses={200: BrandResponseSerializer},
    )
    def get(self, request, brand_id):
        return success_response(data=BrandListSerializer(self.get_brand(brand_id)).data)

    @extend_schema(
        operation_id="admin_brands_update",
        request=BrandUpdateSerializer,
        responses={200: BrandResponseSerializer},
    )
    def patch(self, request, brand_id):
        brand = self.get_brand(brand_id)
        serializer = BrandUpdateSerializer(brand, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        brand = BrandService.update(brand=brand, data=dict(serializer.validated_data))
        return success_response(
            message="Cập nhật thương hiệu thành công",
            data=BrandListSerializer(brand).data,
        )

    @extend_schema(
        operation_id="admin_brands_delete",
        responses={200: DeleteResponseSerializer},
    )
    def delete(self, request, brand_id):
        brand = BrandService.soft_delete(brand=self.get_brand(brand_id))
        return success_response(
            message="Xóa thương hiệu thành công",
            data={"id": str(brand.pk), "is_deleted": True},
        )
