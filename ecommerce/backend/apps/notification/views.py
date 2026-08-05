from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.common.pagination import StandardPagination
from apps.common.responses import success_response

from .serializers import NotificationSerializer
from .services import NotificationService


class NotificationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = NotificationService.list_for_user(request.user)
        unread_count = queryset.filter(is_read=False).count()
        paginator = StandardPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        response = paginator.get_paginated_response(NotificationSerializer(page, many=True).data)
        response.data["meta"]["unread_count"] = unread_count
        return response


class NotificationReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, notification_id):
        notification = get_object_or_404(
            NotificationService.list_for_user(request.user), pk=notification_id
        )
        notification = NotificationService.mark_read(notification)
        return success_response(
            data=NotificationSerializer(notification).data, message="Đã đánh dấu đã đọc"
        )


class NotificationReadAllView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        count = NotificationService.mark_all_read(request.user)
        return success_response(
            data={"updated_count": count}, message="Đã đánh dấu tất cả là đã đọc"
        )
