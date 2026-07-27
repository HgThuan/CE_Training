"""RBAC and tenant-isolation tests for Product endpoints."""

from types import SimpleNamespace

import pytest
from django.urls import reverse
from rest_framework import status

from apps.product.models import Product
from apps.product.permissions import IsShopOwner
from apps.product.tests.factories import (
    ProductFactory,
    ProductMediaFactory,
    ProductVariantFactory,
)


@pytest.mark.django_db
def test_is_shop_owner_checks_product_media_and_variant_ownership(
    seller_user_a,
    seller_user_b,
    product_a,
):
    permission = IsShopOwner()
    owner_request = SimpleNamespace(user=seller_user_a)
    foreign_request = SimpleNamespace(user=seller_user_b)
    media = ProductMediaFactory(product=product_a)
    variant = ProductVariantFactory(product=product_a, shop=product_a.shop)

    for owned_object in (product_a, media, variant):
        assert permission.has_object_permission(owner_request, None, owned_object) is True
        assert permission.has_object_permission(foreign_request, None, owned_object) is False


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("method", "payload"),
    [
        ("patch", {"name": "Không được phép sửa"}),
        ("delete", None),
    ],
)
def test_seller_cannot_edit_or_delete_another_shop_product(
    api_client,
    seller_user_a,
    shop_b,
    category,
    method,
    payload,
):
    victim = ProductFactory(shop=shop_b, category=category)
    api_client.force_authenticate(seller_user_a)
    url = reverse(
        "product:seller-product-detail",
        kwargs={"product_id": victim.pk},
    )

    response = getattr(api_client, method)(url, payload, format="json")

    # The Seller queryset is scoped before object lookup. A 404 avoids exposing
    # whether another shop's product exists while still denying the operation.
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.data["success"] is False
    victim.refresh_from_db()
    assert victim.name != "Không được phép sửa"
    assert victim.is_deleted is False


@pytest.mark.django_db
def test_customer_cannot_call_seller_api_and_seller_cannot_call_admin_api(
    api_client,
    customer_user,
    seller_user_a,
):
    api_client.force_authenticate(customer_user)
    seller_response = api_client.get(reverse("product:seller-product-list"))

    api_client.force_authenticate(seller_user_a)
    admin_response = api_client.get(reverse("product:admin-product-pending"))

    assert seller_response.status_code == status.HTTP_403_FORBIDDEN
    assert seller_response.data["success"] is False
    assert admin_response.status_code == status.HTTP_403_FORBIDDEN
    assert admin_response.data["success"] is False


@pytest.mark.django_db
def test_unauthenticated_user_can_only_read_public_product_endpoints(
    api_client,
    product_a,
):
    product_a.status = Product.Status.APPROVED
    product_a.save(update_fields=("status", "updated_at"))

    public_list = api_client.get(reverse("product:public-product-list"))
    public_detail = api_client.get(
        reverse(
            "product:public-product-detail",
            kwargs={"slug": product_a.slug},
        )
    )
    seller_list = api_client.get(reverse("product:seller-product-list"))
    admin_pending = api_client.get(reverse("product:admin-product-pending"))

    assert public_list.status_code == status.HTTP_200_OK
    assert public_detail.status_code == status.HTTP_200_OK
    assert seller_list.status_code == status.HTTP_401_UNAUTHORIZED
    assert admin_pending.status_code == status.HTTP_401_UNAUTHORIZED
    assert seller_list.data["success"] is False
    assert admin_pending.data["success"] is False
