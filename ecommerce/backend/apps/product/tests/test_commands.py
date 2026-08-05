from io import StringIO

import pytest
from django.core.management import call_command

from apps.account.models import SellerProfile, Shop, User
from apps.inventory.models import InventoryBalance
from apps.product.models import Product, ProductMedia, ProductVariant

pytestmark = pytest.mark.django_db


def test_seed_products_creates_public_products_and_is_idempotent():
    output = StringIO()

    call_command("seed_products", count=3, stock=17, stdout=output)
    call_command("seed_products", count=3, stock=17, stdout=output)

    shop = Shop.objects.get(slug="tech-demo-store")
    owner = shop.owner
    assert owner.role == User.Role.SELLER
    assert not owner.has_usable_password()
    assert SellerProfile.objects.get(user=owner).onboarding_status == "approved"
    assert Product.objects.filter(shop=shop, status=Product.Status.APPROVED).count() == 3
    assert ProductVariant.objects.filter(shop=shop).count() == 6
    assert ProductMedia.objects.filter(product__shop=shop, is_primary=True).count() == 3
    assert (
        InventoryBalance.objects.filter(
            variant__shop=shop,
            available_stock=17,
        ).count()
        == 6
    )


def test_seed_products_does_not_reset_existing_inventory():
    call_command("seed_products", count=1, stock=17)
    balance = InventoryBalance.objects.get(variant__sku="DEMO-01-01")
    balance.available_stock = 4
    balance.save(update_fields=["available_stock", "updated_at"])

    call_command("seed_products", count=1, stock=99)

    balance.refresh_from_db()
    assert balance.available_stock == 4
