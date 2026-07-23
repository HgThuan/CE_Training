import pytest
from django.db import IntegrityError

from apps.account.models import Address, AdminProfile, User


@pytest.mark.django_db
def test_user_manager_normalizes_email_and_hashes_password():
    user = User.objects.create_user(email="  Customer@EXAMPLE.COM ", password="StrongPass!234")

    assert user.email == "customer@example.com"
    assert user.check_password("StrongPass!234")
    assert user.role == User.Role.CUSTOMER


@pytest.mark.django_db(transaction=True)
def test_email_is_case_insensitive_unique():
    User.objects.create_user(email="customer@example.com", password="StrongPass!234")

    with pytest.raises(IntegrityError):
        User.objects.create_user(email="CUSTOMER@example.com", password="StrongPass!234")


@pytest.mark.django_db
def test_create_superuser_has_admin_profile():
    user = User.objects.create_superuser(email="root@example.com", password="StrongPass!234")

    assert user.role == User.Role.ADMIN
    assert user.is_email_verified is True
    assert AdminProfile.objects.filter(user=user).exists()


@pytest.mark.django_db(transaction=True)
def test_user_cannot_have_two_active_default_addresses():
    user = User.objects.create_user(email="address@example.com", password="StrongPass!234")
    address_data = {
        "user": user,
        "recipient_name": "Customer",
        "phone": "0901234567",
        "province": "Hà Nội",
        "district": "Cầu Giấy",
        "ward": "Dịch Vọng",
        "detail_address": "Số 1",
        "is_default": True,
    }
    Address.objects.create(**address_data)

    with pytest.raises(IntegrityError):
        Address.objects.create(**address_data)
