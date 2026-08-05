from channels.generic.websocket import AsyncJsonWebsocketConsumer


class NotificationConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope["user"]
        if not user.is_authenticated:
            await self.close(code=4401)
            return
        self.group_name = f"user_{user.pk}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        protocol = "jwt" if "jwt" in self.scope.get("subprotocols", []) else None
        await self.accept(subprotocol=protocol)

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def notification_created(self, event):
        await self.send_json({"type": "notification", "data": event["notification"]})
