from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.account.models import Shop, User
from apps.common.pagination import StandardPagination
from apps.common.responses import success_response

from .selectors import conversations_for_user, messages_for_conversation
from .serializers import (
    ConversationOpenSerializer,
    ConversationSerializer,
    MessageSerializer,
    MessageWriteSerializer,
    ReadCursorSerializer,
)
from .services import ConversationService


def _conversation_for_user(user, conversation_id):
    return get_object_or_404(conversations_for_user(user), pk=conversation_id)


class ConversationListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role not in (User.Role.CUSTOMER, User.Role.SELLER):
            return success_response(data=[])
        queryset = conversations_for_user(request.user)
        paginator = StandardPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = ConversationSerializer(page, many=True, context={"request": request})
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer = ConversationOpenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        lookup = (
            {"pk": serializer.validated_data["shop_id"]}
            if serializer.validated_data.get("shop_id")
            else {"slug": serializer.validated_data["shop_slug"]}
        )
        shop = get_object_or_404(Shop, **lookup)
        conversation, created = ConversationService.open(customer=request.user, shop=shop)
        return success_response(
            data=ConversationSerializer(conversation, context={"request": request}).data,
            message="Đã mở hội thoại" if created else "Hội thoại đã tồn tại",
            status_code=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class ConversationMessageListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, conversation_id):
        conversation = _conversation_for_user(request.user, conversation_id)
        queryset = messages_for_conversation(conversation)
        latest_first = request.query_params.get("latest", "").lower() == "true"
        after = request.query_params.get("after")
        if after:
            cursor = queryset.filter(pk=after).first()
            if cursor:
                queryset = queryset.filter(created_at__gte=cursor.created_at).exclude(pk=cursor.pk)
        if latest_first:
            queryset = queryset.order_by("-created_at", "-pk")
        paginator = StandardPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        data = list(MessageSerializer(page, many=True).data)
        if latest_first:
            data.reverse()
        return paginator.get_paginated_response(data)

    def post(self, request, conversation_id):
        conversation = _conversation_for_user(request.user, conversation_id)
        serializer = MessageWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        message, created = ConversationService.send_message(
            conversation=conversation, sender=request.user, **serializer.validated_data
        )
        message = messages_for_conversation(conversation).get(pk=message.pk)
        return success_response(
            data=MessageSerializer(message).data,
            message="Đã gửi tin nhắn" if created else "Tin nhắn đã được ghi nhận",
            status_code=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class ConversationReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, conversation_id):
        conversation = _conversation_for_user(request.user, conversation_id)
        serializer = ReadCursorSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        message = ConversationService.mark_read(
            conversation=conversation, user=request.user, **serializer.validated_data
        )
        return success_response(
            data={"last_read_message_id": str(message.pk) if message else None},
            message="Đã đánh dấu hội thoại là đã đọc",
        )
