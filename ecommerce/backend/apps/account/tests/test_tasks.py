import re
from unittest.mock import patch

import pytest
from django.core import mail

from apps.account.models import CustomerProfile, User
from apps.account.tasks import _send_one_email, send_password_reset_email, send_verification_email


@pytest.mark.django_db
def test_auth_email_tasks_include_frontend_links(settings):
    settings.FRONTEND_URL = "https://frontend.example"
    user = User.objects.create_user(email="mail@example.com", password="StrongPass!234")
    CustomerProfile.objects.create(user=user)

    verification_sent = send_verification_email(user.pk)
    user.is_email_verified = True
    user.save(update_fields=["is_email_verified"])
    reset_sent = send_password_reset_email(user.pk)

    assert verification_sent == 1
    assert reset_sent == 1
    assert len(mail.outbox) == 2
    assert "https://frontend.example/auth/verify-email?token=" in mail.outbox[0].body
    assert re.search(r"/auth/reset-password\?uid=[^&]+&token=", mail.outbox[1].body)


@pytest.mark.django_db
def test_admin_password_reset_email_explains_the_forced_reset(settings):
    settings.FRONTEND_URL = "https://frontend.example"
    user = User.objects.create_user(
        email="managed@example.com",
        password="StrongPass!234",
        is_email_verified=True,
    )
    CustomerProfile.objects.create(user=user)

    send_password_reset_email(user.pk, admin_initiated=True)

    assert len(mail.outbox) == 1
    assert "Admin yêu cầu đặt lại mật khẩu" in mail.outbox[0].subject
    assert "Quản trị viên đã thu hồi mật khẩu" in mail.outbox[0].body


def test_email_delivery_rejects_a_zero_backend_result():
    with (
        patch("apps.account.tasks.send_mail", return_value=0),
        pytest.raises(RuntimeError, match="không chấp nhận thư"),
    ):
        _send_one_email(
            subject="Test",
            message="Test",
            from_email="sender@example.com",
            recipient_list=["recipient@example.com"],
        )
