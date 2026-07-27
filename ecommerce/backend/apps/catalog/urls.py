from django.urls import path

from .views import (
    AdminBrandDetailView,
    AdminBrandListCreateView,
    AdminCategoryDetailView,
    AdminCategoryListCreateView,
    AdminCategoryReorderView,
    PublicBrandListView,
    PublicCategoryTreeView,
)

app_name = "catalog"

urlpatterns = [
    path("categories/", PublicCategoryTreeView.as_view(), name="public-category-tree"),
    path("brands/", PublicBrandListView.as_view(), name="public-brand-list"),
    path(
        "admin/categories/",
        AdminCategoryListCreateView.as_view(),
        name="admin-category-list",
    ),
    path(
        "admin/categories/reorder/",
        AdminCategoryReorderView.as_view(),
        name="admin-category-reorder",
    ),
    path(
        "admin/categories/<uuid:category_id>/",
        AdminCategoryDetailView.as_view(),
        name="admin-category-detail",
    ),
    path(
        "admin/brands/",
        AdminBrandListCreateView.as_view(),
        name="admin-brand-list",
    ),
    path(
        "admin/brands/<uuid:brand_id>/",
        AdminBrandDetailView.as_view(),
        name="admin-brand-detail",
    ),
]
