from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from .models import Conversation
from .selectors import messages_for_conversation
from .serializers import MessageSerializer, MessageWriteSerializer
from .services import ConversationService


@database_sync_to_async
def _can_join(user, conversation_id):
    return Conversation.objects.filter(
        pk=conversation_id, participants__user=user, participants__left_at__isnull=True
    ).exists()


@database_sync_to_async
def _send(conversation_id, user, payload):
    serializer = MessageWriteSerializer(data=payload)
    serializer.is_valid(raise_exception=True)
    conversation = Conversation.objects.get(pk=conversation_id)
    message, _ = ConversationService.send_message(
        conversation=conversation, sender=user, **serializer.validated_data
    )
    return MessageSerializer(messages_for_conversation(conversation).get(pk=message.pk)).data


class ChatConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope["user"]
        self.conversation_id = self.scope["url_route"]["kwargs"]["conversation_id"]
        self.group_name = f"conversation_{self.conversation_id}"
        if not user.is_authenticated or not await _can_join(user, self.conversation_id):
            await self.close(code=4403)
            return
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        protocol = "jwt" if "jwt" in self.scope.get("subprotocols", []) else None
        await self.accept(subprotocol=protocol)

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, content, **kwargs):
        try:
            await _send(self.conversation_id, self.scope["user"], content)
        except Exception:
            await self.send_json({"type": "error", "message": "Tin nhắn không hợp lệ"})

    async def chat_message(self, event):
        await self.send_json({"type": "message", "data": event["message"]})
