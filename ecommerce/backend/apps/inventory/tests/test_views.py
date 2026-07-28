import pytest
from django.urls import reverse

from apps.inventory.models import InventoryBalance, StockEntry, StockMovement, StockOutEntry
from apps.inventory.services import StockService
from apps.inventory.tests.factories import InventoryBalanceFactory
from apps.product.models import Product

pytestmark = pytest.mark.django_db


def _entry_payload(variant):
    return {
        "supplier_name": "Nhà cung cấp API",
        "note": "Nhập qua API",
        "items": [
            {
                "variant_id": str(variant.pk),
                "quantity": 8,
                "unit_cost": "50000",
            }
        ],
    }


def test_inventory_list_is_paginated_and_tenant_scoped(
    api_client,
    seller_a,
    variant_a,
    variant_b,
):
    InventoryBalanceFactory(variant=variant_a, available_stock=3)
    InventoryBalanceFactory(variant=variant_b, available_stock=99)
    api_client.force_authenticate(seller_a)

    response = api_client.get(reverse("inventory:seller-inventory-list"))

    assert response.status_code == 200
    assert response.data["success"] is True
    assert response.data["meta"]["total_items"] == 1
    assert response.data["data"][0]["variant_id"] == str(variant_a.pk)
    assert response.data["data"][0]["available_stock"] == 3


def test_inventory_low_stock_filter(api_client, seller_a, variant_a):
    InventoryBalanceFactory(
        variant=variant_a,
        available_stock=6,
        low_stock_threshold=5,
    )
    api_client.force_authenticate(seller_a)

    response = api_client.get(
        reverse("inventory:seller-inventory-list"),
        {"low_stock": "true"},
    )

    assert response.status_code == 200
    assert response.data["data"] == []


def test_stock_entry_create_patch_confirm_and_movement_api(
    api_client,
    seller_a,
    variant_a,
):
    api_client.force_authenticate(seller_a)
    create_response = api_client.post(
        reverse("inventory:seller-stock-entry-list"),
        _entry_payload(variant_a),
        format="json",
    )
    assert create_response.status_code == 201
    assert create_response.data["data"]["status"] == StockEntry.Status.DRAFT
    entry_id = create_response.data["data"]["id"]

    patch_response = api_client.patch(
        reverse("inventory:seller-stock-entry-detail", args=[entry_id]),
        {"note": "Ghi chú đã sửa"},
        format="json",
    )
    assert patch_response.status_code == 200
    assert patch_response.data["data"]["note"] == "Ghi chú đã sửa"

    confirm_response = api_client.post(
        reverse("inventory:seller-stock-entry-confirm", args=[entry_id]),
        format="json",
    )
    assert confirm_response.status_code == 200
    assert confirm_response.data["data"]["status"] == StockEntry.Status.CONFIRMED

    list_response = api_client.get(reverse("inventory:seller-stock-entry-list"))
    movement_response = api_client.get(
        reverse("inventory:seller-inventory-movements"),
        {"variant_id": str(variant_a.pk)},
    )
    assert list_response.status_code == 200
    assert list_response.data["meta"]["total_items"] == 1
    assert movement_response.status_code == 200
    assert movement_response.data["data"][0]["balance_after"] == 8


def test_seller_cannot_confirm_or_filter_by_other_shop_variant(
    api_client,
    seller_a,
    seller_b,
    variant_a,
    variant_b,
):
    entry = StockService.create_stock_entry(
        user=seller_a,
        data=_entry_payload(variant_a),
    )
    api_client.force_authenticate(seller_b)

    confirm_response = api_client.post(
        reverse("inventory:seller-stock-entry-confirm", args=[entry.pk]),
        format="json",
    )
    movement_response = api_client.get(
        reverse("inventory:seller-inventory-movements"),
        {"variant_id": str(variant_a.pk)},
    )
    threshold_response = api_client.post(
        reverse("inventory:seller-inventory-threshold", args=[variant_a.pk]),
        {"low_stock_threshold": 2},
        format="json",
    )

    assert confirm_response.status_code == 404
    assert movement_response.status_code == 404
    assert threshold_response.status_code == 404
    assert not InventoryBalance.objects.filter(variant=variant_b).exists()


def test_stock_out_create_patch_confirm(api_client, seller_a, balance_a):
    api_client.force_authenticate(seller_a)
    create_response = api_client.post(
        reverse("inventory:seller-stock-out-entry-list"),
        {
            "entry_type": StockOutEntry.EntryType.OUT,
            "reason": "Bao bì hỏng",
            "items": [{"variant_id": str(balance_a.variant_id), "quantity": 2}],
        },
        format="json",
    )
    assert create_response.status_code == 201
    entry_id = create_response.data["data"]["id"]

    patch_response = api_client.patch(
        reverse("inventory:seller-stock-out-entry-detail", args=[entry_id]),
        {"reason": "Hàng hỏng do vận chuyển"},
        format="json",
    )
    confirm_response = api_client.post(
        reverse("inventory:seller-stock-out-entry-confirm", args=[entry_id]),
        format="json",
    )
    list_response = api_client.get(reverse("inventory:seller-stock-out-entry-list"))

    balance_a.refresh_from_db()
    assert patch_response.status_code == 200
    assert confirm_response.status_code == 200
    assert list_response.status_code == 200
    assert balance_a.available_stock == 8
    assert StockMovement.objects.filter(movement_type=StockMovement.MovementType.OUT).count() == 1


def test_stock_out_requires_reason(api_client, seller_a, variant_a):
    api_client.force_authenticate(seller_a)

    response = api_client.post(
        reverse("inventory:seller-stock-out-entry-list"),
        {
            "entry_type": StockOutEntry.EntryType.OUT,
            "reason": "",
            "items": [{"variant_id": str(variant_a.pk), "quantity": 1}],
        },
        format="json",
    )

    assert response.status_code == 400
    assert response.data["success"] is False


def test_threshold_update(api_client, seller_a, balance_a):
    api_client.force_authenticate(seller_a)

    response = api_client.post(
        reverse(
            "inventory:seller-inventory-threshold",
            args=[balance_a.variant_id],
        ),
        {"low_stock_threshold": 12},
        format="json",
    )

    assert response.status_code == 200
    balance_a.refresh_from_db()
    assert balance_a.low_stock_threshold == 12
    assert response.data["data"]["is_low_stock"] is True


def test_customer_waitlist_is_idempotent(
    api_client,
    customer,
    variant_a,
):
    variant_a.product.status = Product.Status.APPROVED
    variant_a.product.save(update_fields=["status", "updated_at"])
    InventoryBalanceFactory(variant=variant_a, available_stock=0)
    api_client.force_authenticate(customer)
    url = reverse("inventory:customer-stock-waitlist", args=[variant_a.pk])

    first = api_client.post(url, format="json")
    second = api_client.post(url, format="json")

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.data["data"]["id"] == second.data["data"]["id"]


def test_seller_cannot_register_customer_waitlist(
    api_client,
    seller_a,
    variant_a,
):
    api_client.force_authenticate(seller_a)

    response = api_client.post(
        reverse("inventory:customer-stock-waitlist", args=[variant_a.pk]),
        format="json",
    )

    assert response.status_code == 403
