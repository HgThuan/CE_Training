from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction
from django.utils import timezone

from apps.account.models import Notification


class NotificationService:
    @staticmethod
    def list_for_user(user):
        return Notification.objects.filter(user=user, is_deleted=False)

    @classmethod
    @transaction.atomic
    def mark_read(cls, notification: Notification):
        if not notification.is_read:
            notification.is_read = True
            notification.read_at = timezone.now()
            notification.save(update_fields=("is_read", "read_at", "updated_at"))
        return notification

    @classmethod
    @transaction.atomic
    def mark_all_read(cls, user) -> int:
        return (
            cls.list_for_user(user)
            .filter(is_read=False)
            .update(is_read=True, read_at=timezone.now(), updated_at=timezone.now())
        )

    @staticmethod
    def broadcast(notification_id: int) -> None:
        from .serializers import NotificationSerializer

        notification = Notification.objects.filter(pk=notification_id, is_deleted=False).first()
        if notification is None:
            return
        async_to_sync(get_channel_layer().group_send)(
            f"user_{notification.user_id}",
            {
                "type": "notification.created",
                "notification": NotificationSerializer(notification).data,
            },
        )
