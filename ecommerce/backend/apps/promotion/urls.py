from django.urls import path

from apps.promotion.views import (
    ActiveFlashSaleListView,
    AdminFlashSaleCatalogView,
    AdminFlashSaleDetailView,
    AdminFlashSaleListCreateView,
    AdminVoucherDetailView,
    AdminVoucherListCreateView,
    AvailableVoucherListView,
    CheckoutApplyVoucherByCodeView,
    CheckoutApplyVoucherView,
    CheckoutAvailableVoucherView,
    MyVoucherListView,
    SellerVoucherDetailView,
    SellerVoucherListCreateView,
    ShopVoucherListView,
    VoucherCenterView,
    VoucherCollectView,
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
    path("voucher-center", VoucherCenterView.as_view(), name="voucher-center"),
    path(
        "vouchers/<uuid:campaign_id>/collect",
        VoucherCollectView.as_view(),
        name="voucher-collect",
    ),
    path("me/vouchers", MyVoucherListView.as_view(), name="my-vouchers"),
    path(
        "checkout/available-vouchers",
        CheckoutAvailableVoucherView.as_view(),
        name="checkout-available-vouchers",
    ),
    path(
        "checkout/apply-voucher",
        CheckoutApplyVoucherView.as_view(),
        name="checkout-apply-voucher",
    ),
    path(
        "checkout/apply-voucher-by-code",
        CheckoutApplyVoucherByCodeView.as_view(),
        name="checkout-apply-voucher-by-code",
    ),
    path(
        "shops/<int:shop_id>/vouchers",
        ShopVoucherListView.as_view(),
        name="shop-vouchers-public",
    ),
    path(
        "admin/flash-sales",
        AdminFlashSaleListCreateView.as_view(),
        name="admin-flash-sales",
    ),
    path(
        "admin/flash-sales/catalog",
        AdminFlashSaleCatalogView.as_view(),
        name="admin-flash-sale-catalog",
    ),
    path(
        "admin/flash-sales/<uuid:pk>",
        AdminFlashSaleDetailView.as_view(),
        name="admin-flash-sale-detail",
    ),
    path("flash-sales/active", ActiveFlashSaleListView.as_view(), name="active-flash-sales"),
]
