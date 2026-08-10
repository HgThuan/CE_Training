from django.urls import path

from apps.cart.views import (
    CartDetailView,
    CartItemCreateView,
    CartItemUpdateDeleteView,
    CartMergeView,
    CartPreviewView,
)

app_name = "cart"

urlpatterns = [
    path("", CartDetailView.as_view(), name="detail"),
    path("items", CartItemCreateView.as_view(), name="item-create"),
    path("items/<uuid:item_id>", CartItemUpdateDeleteView.as_view(), name="item-detail"),
    path("merge", CartMergeView.as_view(), name="merge"),
    path("preview", CartPreviewView.as_view(), name="preview"),
]
