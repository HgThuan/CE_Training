from io import StringIO

import pytest
from django.core.management import call_command

from apps.account.models import SellerProfile, Shop, User
from apps.inventory.models import InventoryBalance
from apps.product.management.commands.seed_products import PRODUCTS
from apps.product.models import Product, ProductAttributeValue, ProductMedia, ProductVariant
from apps.review.models import Review

pytestmark = pytest.mark.django_db


def test_seed_products_do_not_reference_the_known_unavailable_power_bank_image():
    unavailable_photo_id = "photo-1609592424824-4e49b1c6b2b9"

    assert all(unavailable_photo_id not in product["image"] for product in PRODUCTS)


def test_seed_products_creates_public_products_and_is_idempotent():
    output = StringIO()

    call_command(
        "seed_products",
        count=3,
        stock=17,
        reviews_per_product=3,
        stdout=output,
    )
    call_command(
        "seed_products",
        count=3,
        stock=17,
        reviews_per_product=3,
        stdout=output,
    )

    shop = Shop.objects.get(slug="tech-demo-store")
    owner = shop.owner
    assert owner.role == User.Role.SELLER
    assert not owner.has_usable_password()
    assert SellerProfile.objects.get(user=owner).onboarding_status == "approved"
    assert Product.objects.filter(shop=shop, status=Product.Status.APPROVED).count() == 3
    assert ProductVariant.objects.filter(shop=shop).count() == 6
    assert ProductMedia.objects.filter(product__shop=shop, is_primary=True).count() == 3
    assert (
        ProductAttributeValue.objects.filter(
            product__shop=shop,
            attribute_value__attribute__name="Nhu cầu",
        ).count()
        == 3
    )
    assert Review.objects.filter(product__shop=shop, status=Review.Status.VISIBLE).count() == 9
    assert not Product.objects.filter(shop=shop).exclude(rating_count=3).exists()
    assert (
        InventoryBalance.objects.filter(
            variant__shop=shop,
            available_stock=17,
        ).count()
        == 6
    )


def test_seed_products_does_not_reset_existing_inventory():
    call_command("seed_products", count=1, stock=17, reviews_per_product=0)
    balance = InventoryBalance.objects.get(variant__sku="DEMO-01-01")
    balance.available_stock = 4
    balance.save(update_fields=["available_stock", "updated_at"])

    call_command("seed_products", count=1, stock=99, reviews_per_product=0)

    balance.refresh_from_db()
    assert balance.available_stock == 4
