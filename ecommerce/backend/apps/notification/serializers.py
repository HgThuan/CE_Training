from rest_framework import serializers

from apps.account.models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    notification_type = serializers.CharField(source="kind", read_only=True)
    data = serializers.JSONField(source="metadata", read_only=True)

    class Meta:
        model = Notification
        fields = (
            "id",
            "notification_type",
            "title",
            "message",
            "data",
            "is_read",
            "read_at",
            "created_at",
        )
