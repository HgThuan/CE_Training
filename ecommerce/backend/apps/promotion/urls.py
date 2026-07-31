from django.urls import path

from apps.promotion.views import (
    ActiveFlashSaleListView,
    AdminFlashSaleDetailView,
    AdminFlashSaleListCreateView,
    AdminVoucherDetailView,
    AdminVoucherListCreateView,
    AvailableVoucherListView,
    SellerVoucherDetailView,
    SellerVoucherListCreateView,
)

app_name = "promotion"

urlpatterns = [
    path("admin/vouchers", AdminVoucherListCreateView.as_view(), name="admin-vouchers"),
    path(
        "admin/vouchers/<uuid:pk>",
        AdminVoucherDetailView.as_view(),
        name="admin-voucher-detail",
    ),
    path("seller/vouchers", SellerVoucherListCreateView.as_view(), name="seller-vouchers"),
    path(
        "seller/vouchers/<uuid:pk>",
        SellerVoucherDetailView.as_view(),
        name="seller-voucher-detail",
    ),
    path(
        "customer/vouchers/available",
        AvailableVoucherListView.as_view(),
        name="available-vouchers",
    ),
    path(
        "admin/flash-sales",
        AdminFlashSaleListCreateView.as_view(),
        name="admin-flash-sales",
    ),
    path(
        "admin/flash-sales/<uuid:pk>",
        AdminFlashSaleDetailView.as_view(),
        name="admin-flash-sale-detail",
    ),
    path("flash-sales/active", ActiveFlashSaleListView.as_view(), name="active-flash-sales"),
]
