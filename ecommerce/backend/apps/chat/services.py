from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone

from apps.account.models import Notification, Shop, User
from apps.common.exceptions import BusinessError
from apps.order.models import ShopOrder
from apps.product.models import Product

from .models import Conversation, ConversationParticipant, Message, MessageAttachment


class ConversationService:
    @staticmethod
    @transaction.atomic
    def open(*, customer, shop: Shop) -> tuple[Conversation, bool]:
        if customer.role != User.Role.CUSTOMER:
            raise BusinessError("Chỉ khách hàng có thể bắt đầu hội thoại", http_status=403)
        if shop.is_deleted or shop.status != Shop.Status.APPROVED:
            raise BusinessError("Gian hàng không khả dụng", http_status=404)
        try:
            conversation, created = Conversation.objects.get_or_create(
                shop=shop,
                customer=customer,
                status=Conversation.Status.ACTIVE,
            )
        except IntegrityError:
            conversation = Conversation.objects.get(
                shop=shop, customer=customer, status=Conversation.Status.ACTIVE
            )
            created = False
        ConversationParticipant.objects.get_or_create(
            conversation=conversation,
            user=customer,
            defaults={"participant_role": ConversationParticipant.Role.CUSTOMER},
        )
        ConversationParticipant.objects.get_or_create(
            conversation=conversation,
            user=shop.owner,
            defaults={"participant_role": ConversationParticipant.Role.SELLER},
        )
        return conversation, created

    @staticmethod
    def require_participant(conversation: Conversation, user) -> ConversationParticipant:
        participant = ConversationParticipant.objects.filter(
            conversation=conversation, user=user, left_at__isnull=True
        ).first()
        if participant is None:
            raise BusinessError("Không tìm thấy hội thoại", http_status=404)
        return participant

    @classmethod
    @transaction.atomic
    def send_message(
        cls,
        *,
        conversation: Conversation,
        sender,
        message_type: str,
        content: str = "",
        product_id=None,
        shop_order_id=None,
        client_message_id: str | None = None,
        attachments=(),
    ) -> tuple[Message, bool]:
        cls.require_participant(conversation, sender)
        if conversation.status != Conversation.Status.ACTIVE:
            raise BusinessError("Hội thoại đã đóng", http_status=409)

        product = None
        shop_order = None
        if message_type == Message.Type.TEXT and not content.strip():
            raise BusinessError("Nội dung tin nhắn không được để trống")
        if message_type == Message.Type.IMAGE and not attachments:
            raise BusinessError("Tin nhắn ảnh phải có ít nhất một ảnh")
        if message_type == Message.Type.PRODUCT:
            product = Product.objects.filter(
                pk=product_id, shop=conversation.shop, is_deleted=False
            ).first()
            if product is None:
                raise BusinessError("Sản phẩm không thuộc gian hàng này", http_status=404)
        if message_type == Message.Type.ORDER:
            shop_order = ShopOrder.objects.filter(
                pk=shop_order_id,
                shop=conversation.shop,
                order__customer__user=conversation.customer,
            ).first()
            if shop_order is None:
                raise BusinessError("Đơn hàng không thuộc hội thoại này", http_status=404)

        normalized_client_id = (client_message_id or "").strip() or None
        if normalized_client_id:
            existing = Message.objects.filter(
                sender=sender, client_message_id=normalized_client_id
            ).first()
            if existing:
                if existing.conversation_id != conversation.pk:
                    raise BusinessError("Mã tin nhắn đã được sử dụng", http_status=409)
                return existing, False

        message = Message.objects.create(
            conversation=conversation,
            sender=sender,
            message_type=message_type,
            content=content.strip(),
            product=product,
            shop_order=shop_order,
            client_message_id=normalized_client_id,
        )
        MessageAttachment.objects.bulk_create(
            [MessageAttachment(message=message, **attachment) for attachment in attachments]
        )
        recipient_id = (
            conversation.shop.owner_id
            if sender.pk == conversation.customer_id
            else conversation.customer_id
        )
        Notification.objects.create(
            user_id=recipient_id,
            kind=Notification.Kind.CHAT,
            title=f"Tin nhắn mới từ {sender.full_name or sender.email}",
            message=content.strip() or "Bạn có một nội dung mới trong hội thoại.",
            metadata={
                "event": "chat_message",
                "conversation_id": str(conversation.pk),
                "message_id": str(message.pk),
            },
        )
        Conversation.objects.filter(pk=conversation.pk).update(
            last_message_at=message.created_at,
            updated_at=timezone.now(),
        )
        transaction.on_commit(lambda: cls.broadcast(message.pk))
        return message, True

    @staticmethod
    def broadcast(message_id) -> None:
        from .serializers import MessageSerializer

        message = (
            Message.objects.select_related("sender", "product", "shop_order")
            .prefetch_related("attachments")
            .get(pk=message_id)
        )
        async_to_sync(get_channel_layer().group_send)(
            f"conversation_{message.conversation_id}",
            {"type": "chat.message", "message": MessageSerializer(message).data},
        )

    @classmethod
    @transaction.atomic
    def mark_read(cls, *, conversation: Conversation, user, message_id=None):
        participant = cls.require_participant(conversation, user)
        messages = Message.objects.filter(conversation=conversation, is_hidden=False)
        message = messages.filter(pk=message_id).first() if message_id else messages.last()
        if message_id and message is None:
            raise BusinessError("Tin nhắn không thuộc hội thoại", http_status=404)
        participant.last_read_message = message
        participant.save(update_fields=("last_read_message",))
        return message

    @staticmethod
    def unread_count(conversation: Conversation, user) -> int:
        participant = ConversationService.require_participant(conversation, user)
        unread = Message.objects.filter(conversation=conversation, is_hidden=False).exclude(
            sender=user
        )
        if participant.last_read_message_id:
            cursor = (
                Message.objects.filter(pk=participant.last_read_message_id)
                .values_list("created_at", flat=True)
                .first()
            )
            if cursor:
                unread = unread.filter(
                    Q(created_at__gt=cursor)
                    | Q(created_at=cursor, pk__gt=participant.last_read_message_id)
                )
        return unread.count()
