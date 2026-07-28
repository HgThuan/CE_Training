import pytest
from rest_framework.test import APIClient

from apps.account.models import User
from apps.account.tests.factories import ShopFactory, UserFactory
from apps.inventory.tests.factories import InventoryBalanceFactory
from apps.product.tests.factories import ProductFactory, ProductVariantFactory


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def shop_a(db):
    return ShopFactory()


@pytest.fixture
def seller_a(shop_a):
    return shop_a.owner


@pytest.fixture
def shop_b(db):
    return ShopFactory()


@pytest.fixture
def seller_b(shop_b):
    return shop_b.owner


@pytest.fixture
def customer(db):
    return UserFactory(role=User.Role.CUSTOMER)


@pytest.fixture
def variant_a(shop_a):
    return ProductVariantFactory(product=ProductFactory(shop=shop_a), shop=shop_a)


@pytest.fixture
def variant_b(shop_b):
    return ProductVariantFactory(product=ProductFactory(shop=shop_b), shop=shop_b)


@pytest.fixture
def balance_a(variant_a):
    return InventoryBalanceFactory(variant=variant_a)

