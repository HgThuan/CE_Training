from django.db.models import Max

from .models import Conversation, Message


def conversations_for_user(user):
    queryset = Conversation.objects.select_related("shop", "shop__owner", "customer").filter(
        participants__user=user,
        participants__left_at__isnull=True,
    )
    return (
        queryset.annotate(latest_message_at=Max("messages__created_at"))
        .distinct()
        .order_by("-last_message_at", "-created_at", "-id")
    )


def messages_for_conversation(conversation):
    return (
        Message.objects.filter(conversation=conversation, is_hidden=False)
        .select_related("sender", "product", "shop_order")
        .prefetch_related("attachments")
    )
