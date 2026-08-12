from django.urls import path

from . import views

urlpatterns = [
    path("checkout/preview", views.CheckoutPreviewView.as_view()),
    path("checkout/confirm", views.CheckoutConfirmView.as_view()),
    path("orders", views.CustomerOrderListView.as_view()),
    path("orders/<uuid:order_id>", views.CustomerOrderDetailView.as_view()),
    path("orders/<uuid:order_id>/cancel", views.CustomerOrderCancelView.as_view()),
    path("orders/<uuid:order_id>/reorder", views.CustomerOrderReorderView.as_view()),
    path("seller/orders", views.SellerOrderListView.as_view()),
    path("seller/customers", views.SellerCustomerListView.as_view()),
    path(
        "seller/customers/<int:customer_id>/orders",
        views.SellerCustomerOrderListView.as_view(),
    ),
    path("seller/orders/<uuid:shop_order_id>", views.SellerOrderDetailView.as_view()),
    path("seller/orders/<uuid:shop_order_id>/confirm", views.ConfirmOrderView.as_view()),
    path("seller/orders/<uuid:shop_order_id>/pack", views.PackOrderView.as_view()),
    path("seller/orders/<uuid:shop_order_id>/ship", views.ShipOrderView.as_view()),
    path("seller/orders/<uuid:shop_order_id>/complete", views.CompleteOrderView.as_view()),
    path("seller/orders/<uuid:shop_order_id>/cancel", views.CancelSellerOrderView.as_view()),
    path("seller/orders/<uuid:shop_order_id>/packing-slip", views.PackingSlipView.as_view()),
    path("admin/orders", views.AdminOrderListView.as_view()),
    path("admin/orders/<uuid:order_id>", views.AdminOrderDetailView.as_view()),
]
