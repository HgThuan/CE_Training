import pytest
from rest_framework.test import APIClient

from apps.account.models import Notification, User
from apps.account.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


def authenticated_client(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


def test_notification_center_is_user_scoped_and_supports_read_all():
    user = UserFactory(role=User.Role.CUSTOMER)
    other = UserFactory(role=User.Role.CUSTOMER)
    own = Notification.objects.create(
        user=user,
        kind=Notification.Kind.ORDER,
        title="Đơn đã cập nhật",
        message="Đang giao",
    )
    Notification.objects.create(
        user=other,
        kind=Notification.Kind.ORDER,
        title="Thông báo khác",
        message="Không được lộ",
    )
    client = authenticated_client(user)

    listed = client.get("/api/v1/notifications")
    read = client.post(f"/api/v1/notifications/{own.pk}/read", {}, format="json")
    read_all = client.post("/api/v1/notifications/read-all", {}, format="json")

    assert listed.status_code == 200
    assert listed.data["meta"]["unread_count"] == 1
    assert len(listed.data["data"]) == 1
    assert read.data["data"]["is_read"] is True
    assert read.data["data"]["read_at"] is not None
    assert read_all.status_code == 200
