import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.account.models import AdminProfile, CustomerProfile, User


@pytest.fixture(autouse=True)
def clear_throttle_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def customer(db):
    user = User.objects.create_user(
        email="customer@example.com",
        password="StrongPass!234",
        full_name="Test Customer",
        is_email_verified=True,
    )
    CustomerProfile.objects.create(user=user)
    return user


@pytest.fixture
def admin_user(db):
    user = User.objects.create_user(
        email="admin@example.com",
        password="StrongPass!234",
        role=User.Role.ADMIN,
        is_staff=True,
        is_email_verified=True,
    )
    AdminProfile.objects.create(user=user)
    return user
