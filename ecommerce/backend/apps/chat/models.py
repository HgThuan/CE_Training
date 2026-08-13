import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q

from apps.common.models import TimeStampedModel


class Conversation(TimeStampedModel):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Đang hoạt động"
        CLOSED = "CLOSED", "Đã đóng"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    shop = models.ForeignKey("account.Shop", on_delete=models.CASCADE, related_name="conversations")
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="customer_conversations",
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.ACTIVE, db_index=True
    )
    last_message_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        db_table = "conversations"
        ordering = ("-last_message_at", "-created_at")
        constraints = [
            models.UniqueConstraint(
                fields=("shop", "customer"),
                condition=Q(status="ACTIVE"),
                name="chat_active_shop_customer_uniq",
            )
        ]
        indexes = [
            models.Index(fields=("shop", "status"), name="chat_conv_shop_status_idx"),
            models.Index(fields=("customer", "status"), name="chat_conv_cust_status_idx"),
        ]


class ConversationParticipant(models.Model):
    class Role(models.TextChoices):
        CUSTOMER = "CUSTOMER", "Khách hàng"
        SELLER = "SELLER", "Nhà bán"
        ADMIN = "ADMIN", "Quản trị viên"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name="participants"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="conversation_participations",
    )
    participant_role = models.CharField(max_length=20, choices=Role.choices)
    last_read_message = models.ForeignKey(
        "Message",
        on_delete=models.SET_NULL,
        related_name="read_by_participants",
        null=True,
        blank=True,
    )
    joined_at = models.DateTimeField(auto_now_add=True)
    left_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "conversation_participants"
        constraints = [
            models.UniqueConstraint(
                fields=("conversation", "user"), name="chat_conversation_user_uniq"
            )
        ]
        indexes = [models.Index(fields=("user", "left_at"), name="chat_part_user_left_idx")]


class Message(models.Model):
    class Type(models.TextChoices):
        TEXT = "TEXT", "Văn bản"
        IMAGE = "IMAGE", "Hình ảnh"
        PRODUCT = "PRODUCT", "Sản phẩm"
        ORDER = "ORDER", "Đơn hàng"
        SYSTEM = "SYSTEM", "Hệ thống"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name="messages"
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="sent_chat_messages"
    )
    message_type = models.CharField(max_length=20, choices=Type.choices)
    content = models.TextField(blank=True)
    product = models.ForeignKey(
        "product.Product",
        on_delete=models.SET_NULL,
        related_name="chat_messages",
        null=True,
        blank=True,
    )
    shop_order = models.ForeignKey(
        "order.ShopOrder",
        on_delete=models.SET_NULL,
        related_name="chat_messages",
        null=True,
        blank=True,
    )
    client_message_id = models.CharField(max_length=120, null=True, blank=True)
    is_hidden = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "messages"
        ordering = ("created_at", "id")
        constraints = [
            models.UniqueConstraint(
                fields=("sender", "client_message_id"),
                condition=Q(client_message_id__isnull=False),
                name="chat_sender_client_message_uniq",
            )
        ]
        indexes = [
            models.Index(fields=("conversation", "created_at"), name="chat_msg_conv_created_idx")
        ]


class MessageAttachment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name="attachments")
    file_url = models.URLField(max_length=1000)
    mime_type = models.CharField(max_length=100)
    size_bytes = models.PositiveBigIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "message_attachments"
        constraints = [
            models.CheckConstraint(condition=Q(size_bytes__gt=0), name="chat_attach_size_positive")
        ]
