import re

import pytest
from django.core import mail

from apps.account.models import CustomerProfile, User
from apps.account.tasks import send_password_reset_email, send_verification_email


@pytest.mark.django_db
def test_auth_email_tasks_include_frontend_links(settings):
    settings.FRONTEND_URL = "https://frontend.example"
    user = User.objects.create_user(email="mail@example.com", password="StrongPass!234")
    CustomerProfile.objects.create(user=user)

    send_verification_email(user.pk)
    user.is_email_verified = True
    user.save(update_fields=["is_email_verified"])
    send_password_reset_email(user.pk)

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
