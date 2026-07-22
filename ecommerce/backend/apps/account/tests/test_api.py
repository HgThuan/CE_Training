from io import BytesIO
from unittest.mock import patch

import pytest
from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from PIL import Image
from rest_framework_simplejwt.tokens import AccessToken

from apps.account.models import Address, CustomerProfile, SellerProfile, User
from apps.account.services import AccountService
from apps.account.tokens import AuthTokenService, EmailVerificationTokenService
from apps.common.models import AuditLog


@pytest.mark.django_db
def test_register_creates_unverified_customer(api_client, django_capture_on_commit_callbacks):
    with (
        patch("apps.account.tasks.send_verification_email.delay") as send_email,
        django_capture_on_commit_callbacks(execute=True),
    ):
        response = api_client.post(
            reverse("account:register"),
            {
                "email": "New@Example.com",
                "password": "StrongPass!234",
                "password_confirm": "StrongPass!234",
                "full_name": "New Customer",
                "role": "admin",
            },
            format="json",
        )

    assert response.status_code == 201
    assert response.data["success"] is True
    user = User.objects.get(email="new@example.com")
    assert user.role == User.Role.CUSTOMER
    assert user.is_email_verified is False
    assert CustomerProfile.objects.filter(user=user).exists()
    send_email.assert_called_once_with(user.pk)


@pytest.mark.django_db
def test_duplicate_register_returns_standard_error(api_client, customer):
    response = api_client.post(
        reverse("account:register"),
        {
            "email": "CUSTOMER@example.com",
            "password": "StrongPass!234",
            "password_confirm": "StrongPass!234",
        },
        format="json",
    )

    assert response.status_code == 400
    assert response.data["success"] is False
    assert "email" in response.data["errors"]


@pytest.mark.django_db
def test_login_requires_verified_email_and_sets_http_only_cookie(api_client, customer):
    customer.is_email_verified = False
    customer.save(update_fields=["is_email_verified"])
    denied = api_client.post(
        reverse("account:login"),
        {"email": customer.email, "password": "StrongPass!234"},
        format="json",
    )
    assert denied.status_code == 403

    customer.is_email_verified = True
    customer.save(update_fields=["is_email_verified"])
    response = api_client.post(
        reverse("account:login"),
        {"email": customer.email, "password": "StrongPass!234"},
        format="json",
    )

    assert response.status_code == 200
    assert "refresh" not in response.data["data"]
    access = AccessToken(response.data["data"]["access"])
    assert access["role"] == User.Role.CUSTOMER
    assert access["token_version"] == customer.token_version
    cookie = response.cookies[settings.JWT_REFRESH_COOKIE_NAME]
    assert cookie["httponly"] is True


@pytest.mark.django_db
def test_refresh_rotates_and_blacklists_previous_token(api_client, customer):
    login = api_client.post(
        reverse("account:login"),
        {"email": customer.email, "password": "StrongPass!234"},
        format="json",
    )
    previous_refresh = login.cookies[settings.JWT_REFRESH_COOKIE_NAME].value

    refreshed = api_client.post(reverse("account:refresh"), {}, format="json")
    rotated_refresh = refreshed.cookies[settings.JWT_REFRESH_COOKIE_NAME].value
    reused = api_client.post(
        reverse("account:refresh"),
        {"refresh": previous_refresh},
        format="json",
    )

    assert refreshed.status_code == 200
    assert rotated_refresh != previous_refresh
    assert reused.status_code == 401


@pytest.mark.django_db
def test_logout_blacklists_refresh_token(api_client, customer):
    login = api_client.post(
        reverse("account:login"),
        {"email": customer.email, "password": "StrongPass!234"},
        format="json",
    )
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['data']['access']}")
    response = api_client.post(reverse("account:logout"), {}, format="json")
    refresh_after_logout = api_client.post(reverse("account:refresh"), {}, format="json")

    assert response.status_code == 200
    assert response.cookies[settings.JWT_REFRESH_COOKIE_NAME].value == ""
    assert refresh_after_logout.status_code == 400


@pytest.mark.django_db
def test_me_never_accepts_identity_or_role_from_client(api_client, customer):
    api_client.force_authenticate(customer)
    response = api_client.patch(
        reverse("account:me"),
        {
            "id": 999,
            "email": "attacker@example.com",
            "role": "admin",
            "full_name": "Updated Name",
        },
        format="json",
    )

    customer.refresh_from_db()
    assert response.status_code == 200
    assert customer.email == "customer@example.com"
    assert customer.role == User.Role.CUSTOMER
    assert customer.full_name == "Updated Name"


@pytest.mark.django_db
def test_avatar_upload_reencodes_image_and_updates_profile(api_client, customer, tmp_path):
    image_bytes = BytesIO()
    Image.new("RGB", (900, 600), "#4f46e5").save(image_bytes, format="PNG")
    upload = SimpleUploadedFile(
        "avatar.png",
        image_bytes.getvalue(),
        content_type="image/png",
    )
    api_client.force_authenticate(customer)

    with override_settings(MEDIA_ROOT=tmp_path):
        response = api_client.post(
            reverse("account:avatar-upload"),
            {"avatar": upload},
            format="multipart",
        )

        customer.refresh_from_db()
        stored_path = tmp_path / customer.avatar_url.removeprefix(settings.MEDIA_URL)
        assert response.status_code == 200
        assert customer.avatar_url.startswith("/media/avatars/")
        assert stored_path.exists()
        with Image.open(stored_path) as stored_image:
            assert stored_image.format == "JPEG"
            assert max(stored_image.size) == 512


@pytest.mark.django_db
def test_avatar_upload_rejects_spoofed_image(api_client, customer):
    api_client.force_authenticate(customer)
    upload = SimpleUploadedFile("avatar.jpg", b"not-an-image", content_type="image/jpeg")

    response = api_client.post(
        reverse("account:avatar-upload"),
        {"avatar": upload},
        format="multipart",
    )

    customer.refresh_from_db()
    assert response.status_code == 400
    assert customer.avatar_url == ""


@pytest.mark.django_db
def test_password_reset_invalidates_existing_access_token(api_client, customer):
    login = api_client.post(
        reverse("account:login"),
        {"email": customer.email, "password": "StrongPass!234"},
        format="json",
    )
    old_access = login.data["data"]["access"]
    customer.refresh_from_db()
    reset = api_client.post(
        reverse("account:reset-password"),
        {
            "uid": urlsafe_base64_encode(force_bytes(customer.pk)),
            "token": default_token_generator.make_token(customer),
            "new_password": "NewStrongPass!456",
            "new_password_confirm": "NewStrongPass!456",
        },
        format="json",
    )

    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {old_access}")
    me = api_client.get(reverse("account:me"))
    customer.refresh_from_db()
    assert reset.status_code == 200
    assert customer.check_password("NewStrongPass!456")
    assert me.status_code == 401


@pytest.mark.django_db
def test_change_password_requires_old_password_and_revokes_session(api_client, customer):
    login = api_client.post(
        reverse("account:login"),
        {"email": customer.email, "password": "StrongPass!234"},
        format="json",
    )
    access = login.data["data"]["access"]
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    denied = api_client.post(
        reverse("account:change-password"),
        {
            "old_password": "WrongPass!234",
            "new_password": "NewStrongPass!456",
            "new_password_confirm": "NewStrongPass!456",
        },
        format="json",
    )
    changed = api_client.post(
        reverse("account:change-password"),
        {
            "old_password": "StrongPass!234",
            "new_password": "NewStrongPass!456",
            "new_password_confirm": "NewStrongPass!456",
        },
        format="json",
    )
    revoked = api_client.get(reverse("account:me"))

    assert denied.status_code == 400
    assert changed.status_code == 200
    assert revoked.status_code == 401


@pytest.mark.django_db
def test_locked_account_existing_access_token_is_rejected(api_client, customer):
    login = api_client.post(
        reverse("account:login"),
        {"email": customer.email, "password": "StrongPass!234"},
        format="json",
    )
    customer.is_active = False
    customer.save(update_fields=["is_active"])
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['data']['access']}")

    response = api_client.get(reverse("account:me"))

    assert response.status_code == 401


@pytest.mark.django_db
def test_forgot_password_does_not_disclose_account_existence(api_client):
    with patch("apps.account.tasks.send_password_reset_email.delay") as send_email:
        response = api_client.post(
            reverse("account:forgot-password"),
            {"email": "missing@example.com"},
            format="json",
        )

    assert response.status_code == 200
    assert response.data["message"] == "Nếu email tồn tại, hướng dẫn đặt lại mật khẩu sẽ được gửi"
    send_email.assert_not_called()


@pytest.mark.django_db
def test_verify_email_accepts_signed_token_and_rejects_invalid(api_client):
    user = User.objects.create_user(email="verify@example.com", password="StrongPass!234")
    CustomerProfile.objects.create(user=user)

    verified = api_client.post(
        reverse("account:verify-email"),
        {"token": EmailVerificationTokenService.generate(user)},
        format="json",
    )
    invalid = api_client.post(
        reverse("account:verify-email"),
        {"token": "invalid-token"},
        format="json",
    )

    user.refresh_from_db()
    assert verified.status_code == 200
    assert user.is_email_verified is True
    assert invalid.status_code == 400


@pytest.mark.django_db
def test_only_admin_can_assign_role_and_action_is_audited(api_client, customer, admin_user):
    target = User.objects.create_user(
        email="target@example.com",
        password="StrongPass!234",
        is_email_verified=True,
    )
    CustomerProfile.objects.create(user=target)
    target_access = AuthTokenService.issue_pair(target)["access"]

    api_client.force_authenticate(customer)
    denied = api_client.post(
        reverse("account:assign-role", kwargs={"user_id": target.pk}),
        {"role": User.Role.SELLER},
        format="json",
    )
    assert denied.status_code == 403

    api_client.force_authenticate(admin_user)
    allowed = api_client.post(
        reverse("account:assign-role", kwargs={"user_id": target.pk}),
        {"role": User.Role.SELLER},
        format="json",
    )

    target.refresh_from_db()
    api_client.force_authenticate(user=None)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {target_access}")
    revoked = api_client.get(reverse("account:me"))
    assert allowed.status_code == 200
    assert target.role == User.Role.SELLER
    assert SellerProfile.objects.filter(user=target).exists()
    assert AuditLog.objects.filter(actor=admin_user, target_id=target.pk).exists()
    assert revoked.status_code == 401


@pytest.mark.django_db
def test_address_book_keeps_one_default_and_soft_deletes(api_client, customer):
    api_client.force_authenticate(customer)
    first = api_client.post(
        reverse("account:address-list"),
        {
            "recipient_name": "Nguyễn Văn A",
            "phone": "0901234567",
            "province": "Hà Nội",
            "district": "Cầu Giấy",
            "ward": "Dịch Vọng",
            "detail_address": "Số 1 đường Test",
            "is_default": False,
        },
        format="json",
    )
    second = api_client.post(
        reverse("account:address-list"),
        {
            "recipient_name": "Nguyễn Văn A",
            "phone": "0901234567",
            "province": "TP. Hồ Chí Minh",
            "district": "Quận 1",
            "ward": "Bến Nghé",
            "detail_address": "Số 2 đường Test",
            "is_default": True,
        },
        format="json",
    )

    first_address = Address.objects.get(pk=first.data["data"]["id"])
    second_address = Address.objects.get(pk=second.data["data"]["id"])
    assert first.status_code == 201
    assert second.status_code == 201
    assert first_address.is_default is False
    assert second_address.is_default is True

    deleted = api_client.delete(
        reverse("account:address-detail", kwargs={"address_id": second_address.pk}),
    )
    first_address.refresh_from_db()
    second_address.refresh_from_db()
    assert deleted.status_code == 200
    assert second_address.is_deleted is True
    assert first_address.is_default is True


@pytest.mark.django_db
def test_address_book_never_exposes_another_users_address(api_client, customer):
    other = User.objects.create_user(
        email="other@example.com",
        password="StrongPass!234",
        is_email_verified=True,
    )
    CustomerProfile.objects.create(user=other)
    address = Address.objects.create(
        user=other,
        recipient_name="Other",
        phone="0901234567",
        province="Hà Nội",
        district="Cầu Giấy",
        ward="Dịch Vọng",
        detail_address="Private address",
        is_default=True,
    )
    api_client.force_authenticate(customer)

    response = api_client.patch(
        reverse("account:address-detail", kwargs={"address_id": address.pk}),
        {"recipient_name": "Attacker"},
        format="json",
    )

    address.refresh_from_db()
    assert response.status_code == 404
    assert address.recipient_name == "Other"


@pytest.mark.django_db
def test_address_book_is_only_available_to_customers(api_client):
    seller = User.objects.create_user(
        email="seller-address@example.com",
        password="StrongPass!234",
        role=User.Role.SELLER,
        is_email_verified=True,
    )
    SellerProfile.objects.create(user=seller)
    api_client.force_authenticate(seller)

    response = api_client.get(reverse("account:address-list"))

    assert response.status_code == 403


@pytest.mark.django_db
def test_admin_customer_crud_is_searchable_paginated_and_audited(
    api_client,
    admin_user,
    customer,
):
    seller = User.objects.create_user(
        email="seller@example.com",
        password="StrongPass!234",
        role=User.Role.SELLER,
        is_email_verified=True,
    )
    SellerProfile.objects.create(user=seller)
    api_client.force_authenticate(admin_user)

    listed = api_client.get(reverse("account:admin-customer-list"), {"search": "Customer"})
    created = api_client.post(
        reverse("account:admin-customer-list"),
        {
            "email": "managed@example.com",
            "password": "StrongPass!234",
            "password_confirm": "StrongPass!234",
            "full_name": "Managed Customer",
            "phone": "0901234567",
            "is_email_verified": True,
        },
        format="json",
    )
    managed_id = created.data["data"]["id"]
    updated = api_client.patch(
        reverse("account:admin-customer-detail", kwargs={"customer_id": managed_id}),
        {"full_name": "Updated Customer"},
        format="json",
    )
    deleted = api_client.delete(
        reverse("account:admin-customer-detail", kwargs={"customer_id": managed_id}),
    )

    managed = User.objects.get(pk=managed_id)
    assert listed.status_code == 200
    assert listed.data["meta"]["total_items"] == 1
    assert listed.data["data"][0]["id"] == customer.pk
    assert created.status_code == 201
    assert updated.data["data"]["full_name"] == "Updated Customer"
    assert deleted.status_code == 200
    assert managed.is_deleted is True
    assert managed.is_active is False
    assert AuditLog.objects.filter(actor=admin_user, target_id=managed_id).count() == 3


@pytest.mark.django_db
def test_non_admin_cannot_manage_customers(api_client, customer):
    api_client.force_authenticate(customer)

    response = api_client.get(reverse("account:admin-customer-list"))

    assert response.status_code == 403


@pytest.mark.django_db
def test_admin_lock_and_unlock_revoke_sessions_and_send_email(
    api_client,
    customer,
    admin_user,
    django_capture_on_commit_callbacks,
):
    old_access = AuthTokenService.issue_pair(customer)["access"]
    api_client.force_authenticate(admin_user)
    with (
        patch("apps.account.tasks.send_account_status_email.delay") as send_email,
        django_capture_on_commit_callbacks(execute=True),
    ):
        locked = api_client.post(
            reverse("account:lock-user", kwargs={"user_id": customer.pk}),
            {"reason": "Vi phạm điều khoản sử dụng"},
            format="json",
        )

    customer.refresh_from_db()
    assert locked.status_code == 200
    assert customer.is_active is False
    assert customer.lock_reason == "Vi phạm điều khoản sử dụng"
    send_email.assert_called_once_with(customer.pk, False, "Vi phạm điều khoản sử dụng")

    api_client.force_authenticate(user=None)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {old_access}")
    assert api_client.get(reverse("account:me")).status_code == 401

    api_client.credentials()
    api_client.force_authenticate(admin_user)
    with (
        patch("apps.account.tasks.send_account_status_email.delay") as send_email,
        django_capture_on_commit_callbacks(execute=True),
    ):
        unlocked = api_client.post(
            reverse("account:unlock-user", kwargs={"user_id": customer.pk}),
            {"reason": "Đã xác minh và khắc phục"},
            format="json",
        )

    customer.refresh_from_db()
    assert unlocked.status_code == 200
    assert customer.is_active is True
    assert customer.lock_reason == ""
    send_email.assert_called_once_with(customer.pk, True, "Đã xác minh và khắc phục")
    assert AuditLog.objects.filter(target_id=customer.pk, action="lock_user").exists()
    assert AuditLog.objects.filter(target_id=customer.pk, action="unlock_user").exists()


@pytest.mark.django_db
def test_admin_reset_password_revokes_password_and_sends_reset_link(
    api_client,
    customer,
    admin_user,
    django_capture_on_commit_callbacks,
):
    previous_version = customer.token_version
    api_client.force_authenticate(admin_user)
    with (
        patch("apps.account.tasks.send_password_reset_email.delay") as send_email,
        django_capture_on_commit_callbacks(execute=True),
    ):
        response = api_client.post(
            reverse("account:admin-reset-password", kwargs={"user_id": customer.pk}),
            {"reason": "Customer yêu cầu hỗ trợ"},
            format="json",
        )

    customer.refresh_from_db()
    assert response.status_code == 200
    assert customer.has_usable_password() is False
    assert customer.must_change_password is True
    assert customer.token_version == previous_version + 1
    send_email.assert_called_once_with(customer.pk, True)
    assert AuditLog.objects.filter(
        actor=admin_user,
        target_id=customer.pk,
        action="admin_reset_password",
    ).exists()

    token_data = AccountService.password_reset_token_data(customer)
    completed = api_client.post(
        reverse("account:reset-password"),
        {
            **token_data,
            "new_password": "NewStrongPass!456",
            "new_password_confirm": "NewStrongPass!456",
        },
        format="json",
    )
    customer.refresh_from_db()
    assert completed.status_code == 200
    assert customer.check_password("NewStrongPass!456")
    assert customer.must_change_password is False


@pytest.mark.django_db
def test_admin_cannot_lock_or_reset_own_account(api_client, admin_user):
    api_client.force_authenticate(admin_user)

    lock = api_client.post(
        reverse("account:lock-user", kwargs={"user_id": admin_user.pk}),
        {"reason": "Invalid self action"},
        format="json",
    )
    reset = api_client.post(
        reverse("account:admin-reset-password", kwargs={"user_id": admin_user.pk}),
        {"reason": "Invalid self action"},
        format="json",
    )

    admin_user.refresh_from_db()
    assert lock.status_code == 400
    assert reset.status_code == 400
    assert admin_user.is_active is True
    assert admin_user.has_usable_password() is True
