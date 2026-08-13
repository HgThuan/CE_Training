import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("account", "0008_add_chat_notification_kind"),
        ("order", "0001_initial"),
        ("product", "0004_search_indexes"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Conversation",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[("ACTIVE", "Đang hoạt động"), ("CLOSED", "Đã đóng")],
                        db_index=True,
                        default="ACTIVE",
                        max_length=20,
                    ),
                ),
                ("last_message_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                (
                    "customer",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="customer_conversations",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "shop",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="conversations",
                        to="account.shop",
                    ),
                ),
            ],
            options={
                "db_table": "conversations",
                "ordering": ("-last_message_at", "-created_at"),
                "indexes": [
                    models.Index(fields=["shop", "status"], name="chat_conv_shop_status_idx"),
                    models.Index(fields=["customer", "status"], name="chat_conv_cust_status_idx"),
                ],
                "constraints": [
                    models.UniqueConstraint(
                        condition=models.Q(("status", "ACTIVE")),
                        fields=("shop", "customer"),
                        name="chat_active_shop_customer_uniq",
                    )
                ],
            },
        ),
        migrations.CreateModel(
            name="Message",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                (
                    "message_type",
                    models.CharField(
                        choices=[
                            ("TEXT", "Văn bản"),
                            ("IMAGE", "Hình ảnh"),
                            ("PRODUCT", "Sản phẩm"),
                            ("ORDER", "Đơn hàng"),
                            ("SYSTEM", "Hệ thống"),
                        ],
                        max_length=20,
                    ),
                ),
                ("content", models.TextField(blank=True)),
                ("client_message_id", models.CharField(blank=True, max_length=120, null=True)),
                ("is_hidden", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                (
                    "conversation",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="messages",
                        to="chat.conversation",
                    ),
                ),
                (
                    "product",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="chat_messages",
                        to="product.product",
                    ),
                ),
                (
                    "sender",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="sent_chat_messages",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "shop_order",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="chat_messages",
                        to="order.shoporder",
                    ),
                ),
            ],
            options={
                "db_table": "messages",
                "ordering": ("created_at", "id"),
                "indexes": [
                    models.Index(
                        fields=["conversation", "created_at"], name="chat_msg_conv_created_idx"
                    )
                ],
                "constraints": [
                    models.UniqueConstraint(
                        condition=models.Q(("client_message_id__isnull", False)),
                        fields=("sender", "client_message_id"),
                        name="chat_sender_client_message_uniq",
                    )
                ],
            },
        ),
        migrations.CreateModel(
            name="ConversationParticipant",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                (
                    "participant_role",
                    models.CharField(
                        choices=[
                            ("CUSTOMER", "Khách hàng"),
                            ("SELLER", "Nhà bán"),
                            ("ADMIN", "Quản trị viên"),
                        ],
                        max_length=20,
                    ),
                ),
                ("joined_at", models.DateTimeField(auto_now_add=True)),
                ("left_at", models.DateTimeField(blank=True, null=True)),
                (
                    "conversation",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="participants",
                        to="chat.conversation",
                    ),
                ),
                (
                    "last_read_message",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="read_by_participants",
                        to="chat.message",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="conversation_participations",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "conversation_participants",
                "indexes": [
                    models.Index(fields=["user", "left_at"], name="chat_part_user_left_idx")
                ],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("conversation", "user"), name="chat_conversation_user_uniq"
                    )
                ],
            },
        ),
        migrations.CreateModel(
            name="MessageAttachment",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("file_url", models.URLField(max_length=1000)),
                ("mime_type", models.CharField(max_length=100)),
                ("size_bytes", models.PositiveBigIntegerField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "message",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="attachments",
                        to="chat.message",
                    ),
                ),
            ],
            options={
                "db_table": "message_attachments",
                "constraints": [
                    models.CheckConstraint(
                        condition=models.Q(("size_bytes__gt", 0)), name="chat_attach_size_positive"
                    )
                ],
            },
        ),
    ]
