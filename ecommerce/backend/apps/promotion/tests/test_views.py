from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.account.models import CustomerProfile
from apps.account.tests.factories import ShopFactory, UserFactory
from apps.inventory.tests.factories import InventoryBalanceFactory
from apps.product.models import Product
from apps.product.tests.factories import ProductVariantFactory
from apps.promotion.models import FlashSale, FlashSaleItem, Voucher


def voucher_payload(code="SAVE10"):
    now = timezone.now()
    return {
        "code": code,
        "name": code,
        "discount_type": "percentage",
        "discount_value": "10",
        "max_discount_amount": "50000",
        "min_order_amount": "100000",
        "total_usage_limit": 100,
        "usage_limit_per_user": 1,
        "valid_from": (now - timezone.timedelta(minutes=1)).isoformat(),
        "valid_until": (now + timezone.timedelta(days=1)).isoformat(),
        "is_active": True,
    }


@pytest.mark.django_db
def test_admin_platform_voucher_crud_is_paginated():
    admin = UserFactory(role="admin", is_staff=True)
    client = APIClient()
    client.force_authenticate(user=admin)

    created = client.post("/api/v1/admin/vouchers", voucher_payload(), format="json")
    assert created.status_code == 201
    assert created.data["data"]["scope"] == Voucher.Scope.PLATFORM

    listed = client.get("/api/v1/admin/vouchers")
    assert listed.status_code == 200
    assert listed.data["meta"]["total_items"] == 1


@pytest.mark.django_db
def test_seller_cannot_access_another_shop_voucher():
    seller_a = UserFactory(role="seller")
    seller_b = UserFactory(role="seller")
    shop_a = ShopFactory(owner=seller_a)
    shop_b = ShopFactory(owner=seller_b)
    now = timezone.now()
    voucher = Voucher.objects.create(
        scope=Voucher.Scope.SHOP,
        shop=shop_b,
        code="PRIVATE",
        name="Private",
        discount_type=Voucher.DiscountType.FIXED_AMOUNT,
        discount_value=Decimal("1000"),
        valid_from=now - timezone.timedelta(minutes=1),
        valid_until=now + timezone.timedelta(days=1),
    )
    client = APIClient()
    client.force_authenticate(user=seller_a)

    response = client.patch(
        f"/api/v1/seller/vouchers/{voucher.id}",
        {"name": "Stolen"},
        format="json",
    )

    assert shop_a.pk != shop_b.pk
    assert response.status_code == 403
    voucher.refresh_from_db()
    assert voucher.name == "Private"


@pytest.mark.django_db
def test_active_flash_sales_is_public_and_paginated():
    now = timezone.now()
    FlashSale.objects.create(
        name="Active",
        start_time=now - timezone.timedelta(minutes=1),
        end_time=now + timezone.timedelta(minutes=10),
    )

    response = APIClient().get("/api/v1/flash-sales/active")

    assert response.status_code == 200
    assert response.data["success"] is True
    assert response.data["meta"]["total_items"] == 1


@pytest.mark.django_db
def test_active_flash_sales_only_exposes_purchasable_items_with_current_stock():
    now = timezone.now()
    flash_sale = FlashSale.objects.create(
        name="Active",
        start_time=now - timezone.timedelta(minutes=1),
        end_time=now + timezone.timedelta(minutes=10),
    )
    available_variant = ProductVariantFactory(product__status=Product.Status.APPROVED)
    unavailable_variant = ProductVariantFactory(product__status=Product.Status.APPROVED)
    InventoryBalanceFactory(variant=available_variant, available_stock=7)
    InventoryBalanceFactory(variant=unavailable_variant, available_stock=0)
    FlashSaleItem.objects.create(
        flash_sale=flash_sale,
        variant=available_variant,
        sale_price=Decimal("80000"),
        quota=10,
    )
    FlashSaleItem.objects.create(
        flash_sale=flash_sale,
        variant=unavailable_variant,
        sale_price=Decimal("80000"),
        quota=10,
    )

    response = APIClient().get("/api/v1/flash-sales/active")

    assert response.status_code == 200
    items = response.data["data"][0]["items"]
    assert [item["variant"] for item in items] == [available_variant.pk]
    assert items[0]["available_stock"] == 7
    assert items[0]["shop_slug"] == available_variant.shop.slug


@pytest.mark.django_db
def test_admin_flash_sale_catalog_is_readable_and_filterable():
    admin = UserFactory(role="admin", is_staff=True)
    variant = ProductVariantFactory(
        product__name="Chuột không dây",
        product__status=Product.Status.APPROVED,
        stock_quantity=0,
    )
    InventoryBalanceFactory(variant=variant, available_stock=7)
    hidden = ProductVariantFactory(product__status=Product.Status.DRAFT, stock_quantity=4)
    client = APIClient()
    client.force_authenticate(user=admin)

    response = client.get(
        "/api/v1/admin/flash-sales/catalog",
        {"search": "Chuột", "category_id": str(variant.product.category_id)},
    )

    assert response.status_code == 200
    assert response.data["meta"]["total_items"] == 1
    assert response.data["data"][0] == {
        "id": str(variant.pk),
        "sku": variant.sku,
        "name": variant.name,
        "sale_price": "90000",
        "available_stock": 7,
        "product_id": str(variant.product_id),
        "product_name": "Chuột không dây",
        "category_id": str(variant.product.category_id),
        "category_name": variant.product.category.name,
        "shop_id": variant.shop_id,
        "shop_name": variant.shop.name,
        "primary_image": None,
    }
    assert hidden.pk != variant.pk


@pytest.mark.django_db
def test_available_vouchers_requires_customer():
    customer = UserFactory(role="customer")
    CustomerProfile.objects.create(user=customer)
    client = APIClient()
    client.force_authenticate(user=customer)

    response = client.get("/api/v1/customer/vouchers/available")

    assert response.status_code == 200
