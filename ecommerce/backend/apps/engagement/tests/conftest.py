import pytest
from rest_framework.test import APIClient

from apps.account.models import User
from apps.account.tests.factories import ShopFactory, UserFactory
from apps.product.models import Product
from apps.product.tests.factories import ProductFactory


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def customer(db):
    return UserFactory(role=User.Role.CUSTOMER)


@pytest.fixture
def other_customer(db):
    return UserFactory(role=User.Role.CUSTOMER)


@pytest.fixture
def shop(db):
    return ShopFactory()


@pytest.fixture
def seller(shop):
    return shop.owner


@pytest.fixture
def other_seller(db):
    return ShopFactory().owner


@pytest.fixture
def product(shop):
    return ProductFactory(
        shop=shop,
        status=Product.Status.APPROVED,
    )
