from django.urls import path

from .views import (
    AdminBannerDetailView,
    AdminBannerListCreateView,
    AdminBannerReorderView,
    HomePageView,
)

app_name = "storefront"

urlpatterns = [
    path("home/", HomePageView.as_view(), name="home"),
    path(
        "admin/banners/",
        AdminBannerListCreateView.as_view(),
        name="admin-banner-list",
    ),
    path(
        "admin/banners/reorder/",
        AdminBannerReorderView.as_view(),
        name="admin-banner-reorder",
    ),
    path(
        "admin/banners/<uuid:banner_id>/",
        AdminBannerDetailView.as_view(),
        name="admin-banner-detail",
    ),
]
