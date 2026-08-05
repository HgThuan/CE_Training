from rest_framework import serializers

from .models import Conversation, Message, MessageAttachment
from .services import ConversationService


class AttachmentInputSerializer(serializers.Serializer):
    file_url = serializers.URLField(max_length=1000)
    mime_type = serializers.RegexField(r"^image/[a-zA-Z0-9.+-]+$", max_length=100)
    size_bytes = serializers.IntegerField(min_value=1, max_value=10 * 1024 * 1024)


class MessageWriteSerializer(serializers.Serializer):
    message_type = serializers.ChoiceField(choices=Message.Type.choices)
    content = serializers.CharField(required=False, allow_blank=True, max_length=5000)
    product_id = serializers.UUIDField(required=False)
    shop_order_id = serializers.UUIDField(required=False)
    client_message_id = serializers.CharField(required=False, allow_blank=True, max_length=120)
    attachments = AttachmentInputSerializer(many=True, required=False)

    def validate(self, attrs):
        message_type = attrs["message_type"]
        if message_type == Message.Type.PRODUCT and not attrs.get("product_id"):
            raise serializers.ValidationError({"product_id": "Sản phẩm là bắt buộc"})
        if message_type == Message.Type.ORDER and not attrs.get("shop_order_id"):
            raise serializers.ValidationError({"shop_order_id": "Đơn hàng là bắt buộc"})
        if len(attrs.get("attachments", ())) > 5:
            raise serializers.ValidationError({"attachments": "Tối đa 5 ảnh mỗi tin nhắn"})
        return attrs


class MessageAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessageAttachment
        fields = ("id", "file_url", "mime_type", "size_bytes", "created_at")


class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.SerializerMethodField()
    sender_role = serializers.CharField(source="sender.role", read_only=True)
    product_name = serializers.CharField(source="product.name", read_only=True, default=None)
    product_slug = serializers.CharField(source="product.slug", read_only=True, default=None)
    shop_order_code = serializers.CharField(
        source="shop_order.shop_order_code", read_only=True, default=None
    )
    attachments = MessageAttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = Message
        fields = (
            "id",
            "conversation",
            "sender",
            "sender_name",
            "sender_role",
            "message_type",
            "content",
            "product",
            "product_name",
            "product_slug",
            "shop_order",
            "shop_order_code",
            "client_message_id",
            "attachments",
            "created_at",
        )

    @staticmethod
    def get_sender_name(obj):
        return obj.sender.full_name or obj.sender.email


class ConversationSerializer(serializers.ModelSerializer):
    shop_name = serializers.CharField(source="shop.name", read_only=True)
    shop_slug = serializers.CharField(source="shop.slug", read_only=True)
    shop_logo_url = serializers.CharField(source="shop.logo_url", read_only=True)
    customer_name = serializers.SerializerMethodField()
    customer_avatar_url = serializers.CharField(source="customer.avatar_url", read_only=True)
    unread_count = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = (
            "id",
            "shop",
            "shop_name",
            "shop_slug",
            "shop_logo_url",
            "customer",
            "customer_name",
            "customer_avatar_url",
            "status",
            "last_message_at",
            "unread_count",
            "last_message",
            "created_at",
        )

    def get_customer_name(self, obj):
        return obj.customer.full_name or obj.customer.email

    def get_unread_count(self, obj):
        request = self.context.get("request")
        return ConversationService.unread_count(obj, request.user) if request else 0

    @staticmethod
    def get_last_message(obj):
        message = obj.messages.filter(is_hidden=False).select_related("sender").last()
        return MessageSerializer(message).data if message else None


class ConversationOpenSerializer(serializers.Serializer):
    shop_id = serializers.IntegerField(required=False)
    shop_slug = serializers.SlugField(required=False)

    def validate(self, attrs):
        if not attrs.get("shop_id") and not attrs.get("shop_slug"):
            raise serializers.ValidationError("shop_id hoặc shop_slug là bắt buộc")
        return attrs


class ReadCursorSerializer(serializers.Serializer):
    message_id = serializers.UUIDField(required=False, allow_null=True)
