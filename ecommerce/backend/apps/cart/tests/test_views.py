from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.account.models import CustomerProfile
from apps.account.tests.factories import ShopFactory, UserFactory
from apps.inventory.tests.factories import InventoryBalanceFactory
from apps.product.models import Product
from apps.product.tests.factories import ProductVariantFactory


@pytest.fixture
def cart_api_context(db):
    user = UserFactory(role="customer")
    CustomerProfile.objects.create(user=user)
    shop = ShopFactory()
    variant = ProductVariantFactory(
        shop=shop,
        product__shop=shop,
        product__status=Product.Status.APPROVED,
        original_price=Decimal("150000"),
        sale_price=Decimal("120000"),
    )
    InventoryBalanceFactory(variant=variant, available_stock=10)
    client = APIClient()
    client.force_authenticate(user=user)
    return client, variant


@pytest.mark.django_db
def test_cart_api_add_update_delete(cart_api_context):
    client, variant = cart_api_context
    created = client.post(
        "/api/v1/cart/items",
        {"variant_id": str(variant.id), "quantity": 2},
        format="json",
    )
    assert created.status_code == 201
    assert created.data["success"] is True
    item_id = created.data["data"]["shops"][0]["items"][0]["id"]

    updated = client.patch(
        f"/api/v1/cart/items/{item_id}",
        {"quantity": 3, "is_selected": False},
        format="json",
    )
    assert updated.status_code == 200
    assert updated.data["data"]["total_selected_items"] == 0

    deleted = client.delete(f"/api/v1/cart/items/{item_id}")
    assert deleted.status_code == 200
    assert deleted.data["data"]["total_items"] == 0


@pytest.mark.django_db
def test_cart_merge_accepts_local_storage_payload(cart_api_context):
    client, variant = cart_api_context
    response = client.post(
        "/api/v1/cart/merge",
        {"items": [{"variant_id": str(variant.id), "quantity": 2}]},
        format="json",
    )

    assert response.status_code == 200
    assert response.data["data"]["total_items"] == 2


@pytest.mark.django_db
def test_cart_requires_customer_authentication():
    response = APIClient().get("/api/v1/cart/")
    assert response.status_code in {401, 403}
