import pytest
from rest_framework.test import APIClient

from apps.account.models import User
from apps.account.tests.factories import ShopFactory, UserFactory
from apps.catalog.tests.factories import BrandFactory, CategoryFactory
from apps.product.tests.factories import ProductFactory


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def admin_user(db):
    return UserFactory(role=User.Role.ADMIN, is_staff=True)


@pytest.fixture
def customer_user(db):
    return UserFactory(role=User.Role.CUSTOMER)


@pytest.fixture
def shop_a(db):
    return ShopFactory()


@pytest.fixture
def seller_user_a(shop_a):
    return shop_a.owner


@pytest.fixture
def shop_b(db):
    return ShopFactory()


@pytest.fixture
def seller_user_b(shop_b):
    return shop_b.owner


@pytest.fixture
def category(db):
    return CategoryFactory()


@pytest.fixture
def brand(db):
    return BrandFactory()


@pytest.fixture
def product_a(shop_a, category, brand):
    return ProductFactory(
        shop=shop_a,
        category=category,
        brand=brand,
    )


@pytest.fixture
def seller_shop(shop_a):
    """Backward-compatible alias used by the existing Seller API tests."""

    return shop_a


@pytest.fixture
def seller_user(seller_user_a):
    """Backward-compatible alias used by tests that need one Seller."""

    return seller_user_a
