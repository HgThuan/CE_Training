from django.urls import path

from .views import (
    AdminDashboardView,
    AuditLogView,
    ChatbotMetricsView,
    ReportExportView,
    ReportView,
    SellerDashboardView,
    ShopRevenueView,
    SiteSettingView,
)

urlpatterns = [
    path("admin/dashboard/chatbot", ChatbotMetricsView.as_view(), name="admin-chatbot-metrics"),
    path("admin/dashboard/summary/", AdminDashboardView.as_view(), name="admin-dashboard-summary"),
    path(
        "admin/dashboard/revenue-chart/",
        AdminDashboardView.as_view(metric="revenue"),
        name="admin-dashboard-revenue",
    ),
    path(
        "admin/dashboard/top-products/",
        AdminDashboardView.as_view(metric="products"),
        name="admin-dashboard-products",
    ),
    path(
        "admin/shops/<int:shop_id>/revenue/", ShopRevenueView.as_view(), name="admin-shop-revenue"
    ),
    path("admin/reports/top-sellers/", ReportView.as_view(report="sellers"), name="report-sellers"),
    path(
        "admin/reports/top-customers/",
        ReportView.as_view(report="customers"),
        name="report-customers",
    ),
    path(
        "admin/reports/top-categories/",
        ReportView.as_view(report="categories"),
        name="report-categories",
    ),
    path(
        "admin/reports/cancel-return-rate/",
        ReportView.as_view(report="cancel-return"),
        name="report-rates",
    ),
    path("admin/reports/export/", ReportExportView.as_view(), name="report-export"),
    path("admin/audit-logs/", AuditLogView.as_view(), name="audit-logs"),
    path("admin/settings/", SiteSettingView.as_view(), name="site-settings"),
    path(
        "seller/dashboard/summary/", SellerDashboardView.as_view(), name="seller-dashboard-summary"
    ),
    path(
        "seller/dashboard/revenue-chart/",
        SellerDashboardView.as_view(metric="revenue"),
        name="seller-dashboard-revenue",
    ),
    path(
        "seller/dashboard/top-products/",
        SellerDashboardView.as_view(metric="products"),
        name="seller-dashboard-products",
    ),
]
