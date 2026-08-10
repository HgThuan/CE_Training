"""API tests for Seller, Admin, and public product views."""

from decimal import Decimal
from io import BytesIO

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image
from rest_framework import status

from apps.account.models import Shop, User
from apps.account.tests.factories import ShopFactory, UserFactory
from apps.catalog.tests.factories import BrandFactory, CategoryFactory
from apps.common.models import AuditLog
from apps.product.models import Attribute, Product, ProductMedia
from apps.product.tests.factories import (
    AttributeFactory,
    AttributeValueFactory,
    ProductFactory,
    ProductMediaFactory,
    ProductVariantFactory,
)
from apps.promotion.models import FlashSale, FlashSaleItem


def image_upload(name: str = "product.jpg") -> SimpleUploadedFile:
    output = BytesIO()
    Image.new("RGB", (48, 48), color="blue").save(output, format="JPEG")
    return SimpleUploadedFile(name, output.getvalue(), content_type="image/jpeg")


@pytest.mark.django_db
def test_seller_product_crud_uses_authenticated_shop_and_standard_responses(
    api_client,
    seller_shop,
):
    api_client.force_authenticate(seller_shop.owner)
    category = CategoryFactory()
    other_shop = ShopFactory()

    forged = api_client.post(
        reverse("product:seller-product-list"),
        {
            "name": "Forged",
            "category_id": str(category.pk),
            "shop_id": other_shop.pk,
        },
        format="json",
    )
    assert forged.status_code == status.HTTP_400_BAD_REQUEST
    assert forged.data["success"] is False

    created = api_client.post(
        reverse("product:seller-product-list"),
        {
            "name": "Áo sơ mi cao cấp",
            "category_id": str(category.pk),
            "short_description": "Mô tả ngắn",
            "description": "<p>Mô tả <script>alert(1)</script></p>",
        },
        format="json",
    )
    assert created.status_code == status.HTTP_201_CREATED
    assert created.data["success"] is True
    product_id = created.data["data"]["id"]
    product = Product.objects.get(pk=product_id)
    assert product.shop_id == seller_shop.pk
    assert product.status == Product.Status.DRAFT
    assert "<script>" not in product.description

    listed = api_client.get(reverse("product:seller-product-list"))
    assert listed.status_code == status.HTTP_200_OK
    assert listed.data["meta"] == {
        "page": 1,
        "page_size": 20,
        "total_items": 1,
        "total_pages": 1,
    }
    assert listed.data["data"][0]["id"] == product_id

    detail_url = reverse(
        "product:seller-product-detail",
        kwargs={"product_id": product_id},
    )
    detail = api_client.get(detail_url)
    assert detail.status_code == status.HTTP_200_OK
    assert detail.data["data"]["category"]["id"] == str(category.pk)

    updated = api_client.patch(
        detail_url,
        {"name": "Áo sơ mi đã sửa"},
        format="json",
    )
    assert updated.status_code == status.HTTP_200_OK
    assert updated.data["data"]["name"] == "Áo sơ mi đã sửa"

    deleted = api_client.delete(detail_url)
    assert deleted.status_code == status.HTTP_200_OK
    product.refresh_from_db()
    assert product.is_deleted is True


@pytest.mark.django_db
def test_seller_list_search_filter_sort_and_pagination(api_client, seller_shop):
    api_client.force_authenticate(seller_shop.owner)
    first_category = CategoryFactory()
    second_category = CategoryFactory()
    older = ProductFactory(
        shop=seller_shop,
        category=first_category,
        name="Áo xanh",
        status=Product.Status.DRAFT,
        min_price=100,
        sold_count=5,
    )
    ProductFactory(
        shop=seller_shop,
        category=second_category,
        name="Quần đen",
        status=Product.Status.REJECTED,
        min_price=200,
        sold_count=10,
    )
    ProductFactory()

    response = api_client.get(
        reverse("product:seller-product-list"),
        {
            "status": Product.Status.DRAFT,
            "category_id": str(first_category.pk),
            "search": "Áo",
            "sort": "-sold_count",
            "page_size": 1,
        },
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["meta"]["total_items"] == 1
    assert response.data["data"][0]["id"] == str(older.pk)


@pytest.mark.django_db
@pytest.mark.parametrize("method", ["get", "patch", "delete"])
def test_seller_a_cannot_access_seller_b_product_by_changing_url_id(
    api_client,
    seller_shop,
    method,
):
    victim = ProductFactory()
    api_client.force_authenticate(seller_shop.owner)
    url = reverse(
        "product:seller-product-detail",
        kwargs={"product_id": victim.pk},
    )

    if method == "patch":
        response = api_client.patch(url, {"name": "Chiếm quyền"}, format="json")
    else:
        response = getattr(api_client, method)(url)

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.data["success"] is False
    victim.refresh_from_db()
    assert victim.name != "Chiếm quyền"
    assert victim.is_deleted is False


@pytest.mark.django_db
def test_customer_cannot_use_seller_api_and_seller_cannot_use_admin_api(
    api_client,
    customer_user,
    seller_user,
):
    api_client.force_authenticate(customer_user)
    seller_denied = api_client.get(reverse("product:seller-product-list"))
    assert seller_denied.status_code == status.HTTP_403_FORBIDDEN

    api_client.force_authenticate(seller_user)
    admin_denied = api_client.get(reverse("product:admin-product-pending"))
    assert admin_denied.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
@override_settings(
    MAX_IMAGE_UPLOAD_MB=1,
    MEDIA_URL="/media/",
)
def test_seller_media_upload_reorder_delete_and_magic_byte_validation(
    api_client,
    seller_shop,
    tmp_path,
    settings,
):
    settings.MEDIA_ROOT = tmp_path
    product = ProductFactory(shop=seller_shop)
    api_client.force_authenticate(seller_shop.owner)
    upload_url = reverse(
        "product:seller-product-media-upload",
        kwargs={"product_id": product.pk},
    )

    fake = api_client.post(
        upload_url,
        {
            "file": SimpleUploadedFile(
                "fake.jpg",
                b"not-an-image",
                content_type="image/jpeg",
            ),
            "media_type": ProductMedia.MediaType.IMAGE,
        },
        format="multipart",
    )
    assert fake.status_code == status.HTTP_400_BAD_REQUEST
    assert fake.data["success"] is False

    first = api_client.post(
        upload_url,
        {
            "file": image_upload("first.jpg"),
            "media_type": ProductMedia.MediaType.IMAGE,
        },
        format="multipart",
    )
    second = api_client.post(
        upload_url,
        {
            "file": image_upload("second.jpg"),
            "media_type": ProductMedia.MediaType.IMAGE,
        },
        format="multipart",
    )
    assert first.status_code == status.HTTP_201_CREATED
    assert second.status_code == status.HTTP_201_CREATED

    first_id = first.data["data"]["id"]
    second_id = second.data["data"]["id"]
    reordered = api_client.post(
        reverse(
            "product:seller-product-media-reorder",
            kwargs={"product_id": product.pk},
        ),
        {"ordered_ids": [second_id, first_id]},
        format="json",
    )
    assert reordered.status_code == status.HTTP_200_OK
    assert [item["id"] for item in reordered.data["data"]["media"]] == [
        second_id,
        first_id,
    ]

    deleted = api_client.delete(
        reverse(
            "product:seller-product-media-delete",
            kwargs={"product_id": product.pk, "media_id": first_id},
        )
    )
    assert deleted.status_code == status.HTTP_200_OK
    assert not ProductMedia.objects.filter(pk=first_id).exists()


@pytest.mark.django_db
def test_seller_attribute_list_generate_and_update_variants(
    api_client,
    seller_shop,
):
    api_client.force_authenticate(seller_shop.owner)
    product = ProductFactory(shop=seller_shop)
    global_attribute = AttributeFactory(shop=None, name="Màu", code="color")
    own_attribute = AttributeFactory(shop=seller_shop, name="Size", code="size")
    foreign_attribute = AttributeFactory(shop=ShopFactory(), name="Chất liệu", code="material")
    red = AttributeValueFactory(attribute=global_attribute, value="Đỏ")
    blue = AttributeValueFactory(attribute=global_attribute, value="Xanh")
    small = AttributeValueFactory(attribute=own_attribute, value="S")
    AttributeValueFactory(attribute=foreign_attribute, value="Cotton")

    attributes = api_client.get(reverse("product:seller-attribute-list"))
    assert attributes.status_code == status.HTTP_200_OK
    assert {item["id"] for item in attributes.data["data"]} == {
        str(global_attribute.pk),
        str(own_attribute.pk),
    }
    assert attributes.data["meta"]["total_items"] == 2

    generated = api_client.post(
        reverse(
            "product:seller-product-variant-generate",
            kwargs={"product_id": product.pk},
        ),
        {
            "attribute_value_ids": [
                str(red.pk),
                str(blue.pk),
                str(small.pk),
            ]
        },
        format="json",
    )
    assert generated.status_code == status.HTTP_201_CREATED
    assert len(generated.data["data"]) == 2
    variant_id = generated.data["data"][0]["id"]

    updated = api_client.patch(
        reverse(
            "product:seller-product-variant-update",
            kwargs={"product_id": product.pk, "variant_id": variant_id},
        ),
        {
            "barcode": None,
            "original_price": "200000",
            "sale_price": "150000",
            "cost_price": "100000",
            "weight_grams": 500,
        },
        format="json",
    )
    assert updated.status_code == status.HTTP_200_OK
    assert updated.data["data"]["sale_price"] == "150000"
    second_variant_id = generated.data["data"][1]["id"]
    second_updated = api_client.patch(
        reverse(
            "product:seller-product-variant-update",
            kwargs={"product_id": product.pk, "variant_id": second_variant_id},
        ),
        {
            "barcode": None,
            "original_price": "200000",
            "sale_price": "150000",
        },
        format="json",
    )
    assert second_updated.status_code == status.HTTP_200_OK
    assert second_updated.data["data"]["barcode"] is None
    product.refresh_from_db()
    assert product.min_price == 150000
    assert product.max_price == 150000


@pytest.mark.django_db
def test_seller_can_define_shop_attribute_with_values(api_client, seller_shop):
    api_client.force_authenticate(seller_shop.owner)

    response = api_client.post(
        reverse("product:seller-attribute-list"),
        {
            "name": "Màu sắc",
            "display_type": "color",
            "values": [
                {"value": "Đỏ", "color_code": "#ef4444"},
                {"value": "Xanh", "color_code": "#3b82f6"},
            ],
        },
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["data"]["scope"] == "shop"
    assert [item["value"] for item in response.data["data"]["values"]] == ["Đỏ", "Xanh"]
    attribute = Attribute.objects.get(pk=response.data["data"]["id"])
    assert attribute.shop_id == seller_shop.pk
    assert attribute.code == "mau-sac"


@pytest.mark.django_db
@override_settings(MAX_IMAGE_UPLOAD_MB=1, MEDIA_URL="/media/")
def test_variant_stock_image_and_barcode_lookup_are_scoped(
    api_client,
    seller_shop,
    tmp_path,
    settings,
):
    settings.MEDIA_ROOT = tmp_path
    product = ProductFactory(shop=seller_shop)
    variant = ProductVariantFactory(
        product=product,
        shop=seller_shop,
        barcode="8938500001234",
    )
    foreign_variant = ProductVariantFactory(barcode="8938500009999")
    api_client.force_authenticate(seller_shop.owner)

    updated = api_client.patch(
        reverse(
            "product:seller-product-variant-update",
            kwargs={"product_id": product.pk, "variant_id": variant.pk},
        ),
        {"stock_quantity": 25},
        format="json",
    )
    uploaded = api_client.post(
        reverse(
            "product:seller-product-media-upload",
            kwargs={"product_id": product.pk},
        ),
        {
            "file": image_upload("variant.jpg"),
            "media_type": ProductMedia.MediaType.IMAGE,
            "variant_id": str(variant.pk),
        },
        format="multipart",
    )
    found = api_client.get(
        reverse("product:seller-variant-lookup"),
        {"barcode": variant.barcode},
    )
    foreign = api_client.get(
        reverse("product:seller-variant-lookup"),
        {"barcode": foreign_variant.barcode},
    )

    assert updated.status_code == status.HTTP_400_BAD_REQUEST
    assert "module Kho" in str(updated.data["errors"])
    assert uploaded.status_code == status.HTTP_201_CREATED
    assert uploaded.data["data"]["variant_id"] == str(variant.pk)
    assert found.status_code == status.HTTP_200_OK
    assert found.data["data"]["id"] == str(variant.pk)
    assert foreign.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_seller_nested_media_and_variant_routes_are_tenant_scoped(
    api_client,
    seller_shop,
):
    victim_product = ProductFactory()
    media = ProductMediaFactory(product=victim_product)
    variant = ProductVariantFactory(
        product=victim_product,
        shop=victim_product.shop,
    )
    api_client.force_authenticate(seller_shop.owner)

    media_response = api_client.delete(
        reverse(
            "product:seller-product-media-delete",
            kwargs={
                "product_id": victim_product.pk,
                "media_id": media.pk,
            },
        )
    )
    variant_response = api_client.patch(
        reverse(
            "product:seller-product-variant-update",
            kwargs={
                "product_id": victim_product.pk,
                "variant_id": variant.pk,
            },
        ),
        {"sale_price": "10"},
        format="json",
    )

    assert media_response.status_code == status.HTTP_404_NOT_FOUND
    assert variant_response.status_code == status.HTTP_404_NOT_FOUND
    assert ProductMedia.objects.filter(pk=media.pk).exists()


@pytest.mark.django_db
def test_seller_submit_and_admin_approval_rejection_hide_delete_flow(
    api_client,
    seller_shop,
    admin_user,
):
    approved_candidate = ProductFactory(shop=seller_shop)
    ProductVariantFactory(
        product=approved_candidate,
        shop=seller_shop,
    )
    rejected_candidate = ProductFactory(
        shop=seller_shop,
        status=Product.Status.PENDING_REVIEW,
    )

    api_client.force_authenticate(seller_shop.owner)
    submitted = api_client.post(
        reverse(
            "product:seller-product-submit",
            kwargs={"product_id": approved_candidate.pk},
        ),
        format="json",
    )
    assert submitted.status_code == status.HTTP_200_OK
    assert submitted.data["data"]["status"] == Product.Status.PENDING_REVIEW

    api_client.force_authenticate(admin_user)
    pending = api_client.get(reverse("product:admin-product-pending"))
    assert pending.status_code == status.HTTP_200_OK
    assert pending.data["meta"]["total_items"] == 2
    assert pending.data["data"][0]["seller_email"]

    approved = api_client.post(
        reverse(
            "product:admin-product-approve",
            kwargs={"product_id": approved_candidate.pk},
        ),
        format="json",
        HTTP_X_REQUEST_ID="approve-api",
    )
    assert approved.status_code == status.HTTP_200_OK
    assert approved.data["data"]["status"] == Product.Status.APPROVED

    missing_reason = api_client.post(
        reverse(
            "product:admin-product-reject",
            kwargs={"product_id": rejected_candidate.pk},
        ),
        {},
        format="json",
    )
    assert missing_reason.status_code == status.HTTP_400_BAD_REQUEST

    rejected = api_client.post(
        reverse(
            "product:admin-product-reject",
            kwargs={"product_id": rejected_candidate.pk},
        ),
        {"rejection_reason": "Thiếu thông tin"},
        format="json",
    )
    assert rejected.status_code == status.HTTP_200_OK
    assert rejected.data["data"]["status"] == Product.Status.REJECTED

    hidden = api_client.post(
        reverse(
            "product:admin-product-hide",
            kwargs={"product_id": approved_candidate.pk},
        ),
        format="json",
    )
    assert hidden.status_code == status.HTTP_200_OK
    deleted = api_client.delete(
        reverse(
            "product:admin-product-delete",
            kwargs={"product_id": approved_candidate.pk},
        ),
        HTTP_X_REQUEST_ID="delete-api",
    )
    assert deleted.status_code == status.HTTP_200_OK
    approved_candidate.refresh_from_db()
    assert approved_candidate.is_deleted is True
    assert AuditLog.objects.filter(
        target_id=str(approved_candidate.pk),
        action="approve_product",
        request_id="approve-api",
    ).exists()
    assert AuditLog.objects.filter(
        target_id=str(approved_candidate.pk),
        action="delete_product",
        request_id="delete-api",
    ).exists()


@pytest.mark.django_db
def test_non_admin_roles_cannot_approve_reject_hide_or_delete(
    api_client,
    customer_user,
):
    product = ProductFactory(status=Product.Status.PENDING_REVIEW)
    endpoints = [
        (
            "post",
            reverse(
                "product:admin-product-approve",
                kwargs={"product_id": product.pk},
            ),
            {},
        ),
        (
            "post",
            reverse(
                "product:admin-product-reject",
                kwargs={"product_id": product.pk},
            ),
            {"rejection_reason": "Không có quyền"},
        ),
        (
            "post",
            reverse(
                "product:admin-product-hide",
                kwargs={"product_id": product.pk},
            ),
            {},
        ),
        (
            "delete",
            reverse(
                "product:admin-product-delete",
                kwargs={"product_id": product.pk},
            ),
            None,
        ),
    ]
    for user in (customer_user, UserFactory(role=User.Role.SELLER)):
        api_client.force_authenticate(user)
        for method, url, payload in endpoints:
            response = getattr(api_client, method)(url, payload, format="json")
            assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_public_product_list_filters_sorts_and_excludes_non_public_rows(api_client):
    category = CategoryFactory()
    brand = BrandFactory()
    visible = ProductFactory(
        category=category,
        brand=brand,
        status=Product.Status.APPROVED,
        name="Laptop Alpha",
        min_price=100,
        max_price=200,
        sold_count=10,
        rating_average="4.50",
    )
    ProductMediaFactory(product=visible, is_primary=True)
    best_seller = ProductFactory(
        category=category,
        brand=brand,
        status=Product.Status.APPROVED,
        name="Laptop Beta",
        min_price=500,
        max_price=600,
        sold_count=20,
    )
    ProductFactory(category=category, status=Product.Status.DRAFT, name="Laptop Draft")
    locked = ProductFactory(
        category=category,
        status=Product.Status.APPROVED,
        name="Laptop Locked",
    )
    locked.shop.status = Shop.Status.LOCKED
    locked.shop.save(update_fields=("status", "updated_at"))

    sorted_response = api_client.get(
        reverse("product:public-product-list"),
        {
            "category_id": str(category.pk),
            "brand_id": str(brand.pk),
            "sort": "-sold_count",
        },
    )
    response = api_client.get(
        reverse("product:public-product-list"),
        {
            "category_id": str(category.pk),
            "brand_id": str(brand.pk),
            "min_price": "50",
            "max_price": "300",
            "search": "Alpha",
            "sort": "-sold_count",
        },
    )

    assert sorted_response.status_code == status.HTTP_200_OK
    assert [item["id"] for item in sorted_response.data["data"][:2]] == [
        str(best_seller.pk),
        str(visible.pk),
    ]
    assert response.status_code == status.HTTP_200_OK
    assert response.data["meta"]["total_items"] == 1
    assert response.data["data"][0]["id"] == str(visible.pk)
    assert response.data["data"][0]["thumbnail"] is not None
    assert response.data["data"][0]["shop_slug"] == visible.shop.slug


@pytest.mark.django_db
def test_public_product_list_query_count_does_not_scale_with_rows(
    api_client,
    django_assert_max_num_queries,
):
    for index in range(6):
        product = ProductFactory(
            status=Product.Status.APPROVED,
            name=f"Optimized product {index}",
        )
        ProductMediaFactory(product=product)
        ProductVariantFactory(product=product, shop=product.shop)

    # Count + products + images + variants + active Flash Sale items. This
    # remains constant as rows grow.
    with django_assert_max_num_queries(6):
        response = api_client.get(
            reverse("product:public-product-list"),
            {"page_size": 10},
        )

    assert response.status_code == status.HTTP_200_OK
    assert len(response.data["data"]) == 6


@pytest.mark.django_db
def test_public_product_filter_validation_uses_standard_error_response(api_client):
    response = api_client.get(
        reverse("product:public-product-list"),
        {"min_price": "200", "max_price": "100"},
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["success"] is False
    assert "max_price" in response.data["errors"]


@pytest.mark.django_db
def test_public_detail_returns_nested_data_and_hides_private_variant_fields(api_client):
    product = ProductFactory(status=Product.Status.APPROVED)
    product.shop.logo_url = "https://cdn.example.com/shops/public-logo.webp"
    product.shop.save(update_fields=("logo_url", "updated_at"))
    variant = ProductVariantFactory(
        product=product,
        shop=product.shop,
        cost_price=50,
        barcode="PRIVATE-BARCODE",
    )
    ProductMediaFactory(product=product, is_primary=True)

    response = api_client.get(
        reverse(
            "product:public-product-detail",
            kwargs={"slug": product.slug},
        )
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["data"]["shop"]["name"] == product.shop.name
    assert response.data["data"]["shop"]["logo_url"] == product.shop.logo_url
    assert response.data["data"]["category"]["id"] == str(product.category_id)
    assert response.data["data"]["variants"][0]["id"] == str(variant.pk)
    assert "cost_price" not in response.data["data"]["variants"][0]
    assert "barcode" not in response.data["data"]["variants"][0]


@pytest.mark.django_db
def test_public_product_apis_expose_flash_sale_as_effective_price_everywhere(api_client):
    product = ProductFactory(
        status=Product.Status.APPROVED,
        min_price=Decimal("90000"),
        max_price=Decimal("90000"),
    )
    variant = ProductVariantFactory(
        product=product,
        shop=product.shop,
        sale_price=Decimal("90000"),
    )
    sale = FlashSale.objects.create(
        name="Everywhere",
        start_time=timezone.now() - timezone.timedelta(minutes=1),
        end_time=timezone.now() + timezone.timedelta(hours=1),
    )
    FlashSaleItem.objects.create(
        flash_sale=sale,
        variant=variant,
        sale_price=Decimal("60000"),
        quota=5,
    )

    listed = api_client.get(reverse("product:public-product-list"))
    detail = api_client.get(
        reverse("product:public-product-detail", kwargs={"slug": product.slug}),
        {"shop_slug": product.shop.slug},
    )

    listed_product = next(item for item in listed.data["data"] if item["id"] == str(product.pk))
    detail_product = detail.data["data"]
    detail_variant = detail_product["variants"][0]
    assert listed_product["min_price"] == "60000"
    assert listed_product["regular_min_price"] == "90000"
    assert listed_product["is_flash_sale"] is True
    assert detail_product["min_price"] == "60000"
    assert detail_variant["sale_price"] == "60000"
    assert detail_variant["regular_price"] == "90000"
    assert detail_variant["remaining_flash_quota"] == 5


@pytest.mark.django_db
def test_public_duplicate_slug_requires_shop_scope(api_client):
    first = ProductFactory(
        status=Product.Status.APPROVED,
        slug="shared-public-slug",
    )
    ProductFactory(
        status=Product.Status.APPROVED,
        slug="shared-public-slug",
    )
    url = reverse(
        "product:public-product-detail",
        kwargs={"slug": "shared-public-slug"},
    )

    ambiguous = api_client.get(url)
    scoped = api_client.get(url, {"shop_slug": first.shop.slug})

    assert ambiguous.status_code == status.HTTP_400_BAD_REQUEST
    assert ambiguous.data["success"] is False
    assert scoped.status_code == status.HTTP_200_OK
    assert scoped.data["data"]["id"] == str(first.pk)
