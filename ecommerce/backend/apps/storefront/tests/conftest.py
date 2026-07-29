import pytest
from rest_framework.test import APIClient

from apps.account.models import User
from apps.account.tests.factories import UserFactory


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def admin_user(db):
    return UserFactory(role=User.Role.ADMIN, is_staff=True)


@pytest.fixture
def customer_user(db):
    return UserFactory(role=User.Role.CUSTOMER)
