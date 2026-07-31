from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.account.models import CustomerProfile
from apps.account.tests.factories import ShopFactory, UserFactory
from apps.promotion.models import FlashSale, Voucher


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
def test_available_vouchers_requires_customer():
    customer = UserFactory(role="customer")
    CustomerProfile.objects.create(user=customer)
    client = APIClient()
    client.force_authenticate(user=customer)

    response = client.get("/api/v1/customer/vouchers/available")

    assert response.status_code == 200
