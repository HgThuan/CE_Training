from django.urls import path

from .views import (
    AdminProductViewSet,
    PublicProductViewSet,
    SellerProductViewSet,
)

app_name = "product"

seller_product_list = SellerProductViewSet.as_view({"get": "list", "post": "create"})
seller_product_detail = SellerProductViewSet.as_view(
    {
        "get": "retrieve",
        "patch": "partial_update",
        "delete": "destroy",
    }
)
seller_product_submit = SellerProductViewSet.as_view({"post": "submit"})
seller_product_media_upload = SellerProductViewSet.as_view({"post": "upload_media"})
seller_product_media_delete = SellerProductViewSet.as_view({"delete": "delete_media"})
seller_product_media_reorder = SellerProductViewSet.as_view({"post": "reorder_media"})
seller_attribute_list = SellerProductViewSet.as_view({"get": "list_attributes"})
seller_variant_generate = SellerProductViewSet.as_view({"post": "generate_variants"})
seller_variant_update = SellerProductViewSet.as_view({"patch": "update_variant"})

admin_product_pending = AdminProductViewSet.as_view({"get": "list_pending"})
admin_product_list = AdminProductViewSet.as_view({"get": "list"})
admin_product_approve = AdminProductViewSet.as_view({"post": "approve"})
admin_product_reject = AdminProductViewSet.as_view({"post": "reject"})
admin_product_hide = AdminProductViewSet.as_view({"post": "hide"})
admin_product_unhide = AdminProductViewSet.as_view({"post": "unhide"})
admin_product_delete = AdminProductViewSet.as_view({"delete": "destroy"})

public_product_list = PublicProductViewSet.as_view({"get": "list"})
public_product_detail = PublicProductViewSet.as_view({"get": "retrieve"})

urlpatterns = [
    path(
        "seller/products/",
        seller_product_list,
        name="seller-product-list",
    ),
    path(
        "seller/attributes/",
        seller_attribute_list,
        name="seller-attribute-list",
    ),
    path(
        "seller/products/<uuid:product_id>/",
        seller_product_detail,
        name="seller-product-detail",
    ),
    path(
        "seller/products/<uuid:product_id>/submit/",
        seller_product_submit,
        name="seller-product-submit",
    ),
    path(
        "seller/products/<uuid:product_id>/media/",
        seller_product_media_upload,
        name="seller-product-media-upload",
    ),
    path(
        "seller/products/<uuid:product_id>/media/reorder/",
        seller_product_media_reorder,
        name="seller-product-media-reorder",
    ),
    path(
        "seller/products/<uuid:product_id>/media/<uuid:media_id>/",
        seller_product_media_delete,
        name="seller-product-media-delete",
    ),
    path(
        "seller/products/<uuid:product_id>/variants/generate/",
        seller_variant_generate,
        name="seller-product-variant-generate",
    ),
    path(
        "seller/products/<uuid:product_id>/variants/<uuid:variant_id>/",
        seller_variant_update,
        name="seller-product-variant-update",
    ),
    path(
        "admin/products/",
        admin_product_list,
        name="admin-product-list",
    ),
    path(
        "admin/products/pending/",
        admin_product_pending,
        name="admin-product-pending",
    ),
    path(
        "admin/products/<uuid:product_id>/approve/",
        admin_product_approve,
        name="admin-product-approve",
    ),
    path(
        "admin/products/<uuid:product_id>/reject/",
        admin_product_reject,
        name="admin-product-reject",
    ),
    path(
        "admin/products/<uuid:product_id>/hide/",
        admin_product_hide,
        name="admin-product-hide",
    ),
    path(
        "admin/products/<uuid:product_id>/unhide/",
        admin_product_unhide,
        name="admin-product-unhide",
    ),
    path(
        "admin/products/<uuid:product_id>/",
        admin_product_delete,
        name="admin-product-delete",
    ),
    path("products/", public_product_list, name="public-product-list"),
    path(
        "products/<slug:slug>/",
        public_product_detail,
        name="public-product-detail",
    ),
]
