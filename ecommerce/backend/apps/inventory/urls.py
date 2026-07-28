from django.urls import path

from .views import (
    InventoryListView,
    StockAlertCreateView,
    StockEntryConfirmView,
    StockEntryDetailView,
    StockEntryListCreateView,
    StockMovementListView,
    StockOutEntryConfirmView,
    StockOutEntryDetailView,
    StockOutEntryListCreateView,
    ThresholdUpdateView,
)

app_name = "inventory"

urlpatterns = [
    path(
        "seller/inventory/",
        InventoryListView.as_view(),
        name="seller-inventory-list",
    ),
    path(
        "seller/inventory/movements/",
        StockMovementListView.as_view(),
        name="seller-inventory-movements",
    ),
    path(
        "seller/inventory/stock-entries/",
        StockEntryListCreateView.as_view(),
        name="seller-stock-entry-list",
    ),
    path(
        "seller/inventory/stock-entries/<int:entry_id>/",
        StockEntryDetailView.as_view(),
        name="seller-stock-entry-detail",
    ),
    path(
        "seller/inventory/stock-entries/<int:entry_id>/confirm/",
        StockEntryConfirmView.as_view(),
        name="seller-stock-entry-confirm",
    ),
    path(
        "seller/inventory/stock-out-entries/",
        StockOutEntryListCreateView.as_view(),
        name="seller-stock-out-entry-list",
    ),
    path(
        "seller/inventory/stock-out-entries/<int:entry_id>/",
        StockOutEntryDetailView.as_view(),
        name="seller-stock-out-entry-detail",
    ),
    path(
        "seller/inventory/stock-out-entries/<int:entry_id>/confirm/",
        StockOutEntryConfirmView.as_view(),
        name="seller-stock-out-entry-confirm",
    ),
    path(
        "seller/inventory/<uuid:variant_id>/threshold/",
        ThresholdUpdateView.as_view(),
        name="seller-inventory-threshold",
    ),
    path(
        "customer/products/<uuid:variant_id>/waitlist/",
        StockAlertCreateView.as_view(),
        name="customer-stock-waitlist",
    ),
]
