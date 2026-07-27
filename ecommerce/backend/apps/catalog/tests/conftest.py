import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.account.models import User
from apps.account.tests.factories import UserFactory


@pytest.fixture(autouse=True)
def clear_throttle_cache():
    cache.clear()
    yield
    cache.clear()


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
def seller_user(db):
    return UserFactory(role=User.Role.SELLER)
