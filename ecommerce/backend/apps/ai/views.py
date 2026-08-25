import asyncio
import json
import re
import threading
from collections.abc import AsyncIterator
from typing import Any

from django.conf import settings
from django.db import connections
from django.http import StreamingHttpResponse
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import generics
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.renderers import JSONRenderer
from rest_framework.throttling import AnonRateThrottle, SimpleRateThrottle, UserRateThrottle
from rest_framework.views import APIView

from apps.account.permissions import IsSeller
from apps.common.responses import success_response
from apps.product.selectors import ProductSelector
from apps.product.serializers import PublicProductListSerializer

from .assistant import ShoppingAssistant
from .models import ChatFeedback, ChatMessage, ChatSession, sanitize_ai_text
from .permissions import AISearchRateThrottle
from .renderers import ServerSentEventRenderer
from .search_service import AISearchService
from .serializers import (
    AISearchResponseSerializer,
    AssistantConversationDetailSerializer,
    AssistantConversationSerializer,
    AssistantFeedbackSerializer,
    AssistantMessageRequestSerializer,
    ProductAIReviewSummaryResponseSerializer,
    ProductAISummaryResponseSerializer,
    ProductCompareRequestSerializer,
    ProductCompareResponseSerializer,
    SellerListingRequestSerializer,
    SellerListingResponseSerializer,
    SemanticSearchQuerySerializer,
    SmartSearchQuerySerializer,
)
from .services import AIService


class AssistantConversationThrottle(SimpleRateThrottle):
    scope = "ai_chat_session"

    def get_rate(self):
        rates = settings.REST_FRAMEWORK.get("DEFAULT_THROTTLE_RATES", {})
        return rates.get(self.scope, "12/minute")

    def get_cache_key(self, request, view):
        if request.user.is_authenticated:
            ident = f"user:{request.user.pk}"
        else:
            ident = f"guest:{request.data.get('guest_token') or self.get_ident(request)}"
        return self.cache_format % {"scope": self.scope, "ident": ident}


class AssistantMessageView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AssistantConversationThrottle]
    renderer_classes = [ServerSentEventRenderer, JSONRenderer]

    @extend_schema(
        operation_id="ai_assistant_message",
        request=AssistantMessageRequestSerializer,
        responses={(200, "text/event-stream"): str},
    )
    def post(self, request):
        serializer = AssistantMessageRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        owner = _assistant_owner(request, serializer.validated_data)
        conversation_id = serializer.validated_data.get("conversation_id")
        if conversation_id:
            session = get_object_or_404(
                ChatSession,
                pk=conversation_id,
                **owner,
            )
        else:
            session = ChatSession.objects.create(**owner)
        _apply_assistant_context(session, serializer.validated_data)
        message = serializer.validated_data["message"]

        response = StreamingHttpResponse(
            _assistant_event_stream(
                session=session,
                message=message,
                user=request.user if request.user.is_authenticated else None,
            ),
            content_type="text/event-stream; charset=utf-8",
        )
        response["Cache-Control"] = "no-cache, no-transform"
        response["X-Accel-Buffering"] = "no"
        return response


class AssistantConversationListView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        operation_id="ai_assistant_conversation_list",
        responses={200: AssistantConversationSerializer(many=True)},
    )
    def get(self, request):
        conversations = ChatSession.objects.filter(**_assistant_owner(request)).order_by(
            "-last_active_at", "-created_at"
        )[:50]
        return success_response(
            data=AssistantConversationSerializer(conversations, many=True).data
        )


class AssistantConversationDetailView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        operation_id="ai_assistant_conversation_detail",
        responses={200: AssistantConversationDetailSerializer},
    )
    def get(self, request, conversation_id):
        session = get_object_or_404(
            ChatSession,
            pk=conversation_id,
            **_assistant_owner(request),
        )
        messages = (
            session.messages.filter(
                role__in=(ChatMessage.Role.USER, ChatMessage.Role.ASSISTANT)
            )
            .select_related("feedback")
            .order_by("created_at", "id")
        )
        data = AssistantConversationSerializer(session).data
        data["messages"] = [
            ShoppingAssistant.serialize_message(message) for message in messages
        ]
        return success_response(data=data)

    @extend_schema(
        operation_id="ai_assistant_conversation_delete",
        responses={200: AssistantConversationSerializer},
    )
    def delete(self, request, conversation_id):
        session = get_object_or_404(
            ChatSession,
            pk=conversation_id,
            **_assistant_owner(request),
        )
        session.delete()
        return success_response(data=None, message="Đã xóa cuộc trò chuyện.")


class AssistantFeedbackView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        operation_id="ai_assistant_feedback",
        request=AssistantFeedbackSerializer,
        responses={200: AssistantFeedbackSerializer},
    )
    def post(self, request, message_id):
        serializer = AssistantFeedbackSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        owner = _assistant_owner(request, serializer.validated_data)
        message = get_object_or_404(
            ChatMessage.objects.select_related("session"),
            pk=message_id,
            role=ChatMessage.Role.ASSISTANT,
            **{f"session__{key}": value for key, value in owner.items()},
        )
        feedback, _ = ChatFeedback.objects.update_or_create(
            message=message,
            defaults={
                "session": message.session,
                "submitted_by": request.user if request.user.is_authenticated else None,
                "rating": serializer.validated_data["rating"],
                "resolved": serializer.validated_data.get("resolved"),
                "comment": sanitize_ai_text(
                    serializer.validated_data.get("comment", ""),
                    max_length=1_000,
                ),
            },
        )
        return success_response(
            data={
                "rating": feedback.rating,
                "resolved": feedback.resolved,
                "comment": feedback.comment,
            },
            message="Cảm ơn bạn đã phản hồi.",
        )


def _assistant_owner(request, data=None) -> dict:
    """Resolve a conversation owner without mixing authenticated and guest histories."""
    if request.user.is_authenticated:
        return {"user": request.user}

    source = data if data is not None else request.query_params
    guest_token = str(source.get("guest_token", "")).strip()
    if not re.fullmatch(r"[A-Za-z0-9._-]{20,64}", guest_token):
        raise ValidationError(
            {"guest_token": ["Cần mã phiên khách hợp lệ để tiếp tục cuộc trò chuyện."]}
        )
    return {"guest_token": guest_token, "user": None}


def _apply_assistant_context(session: ChatSession, data) -> None:
    context = dict(session.context or {})
    context["channel"] = data.get("channel", context.get("channel", "web"))
    if "browsing_history" in data:
        context["browsing_history"] = [str(item) for item in data["browsing_history"][:20]]

    session.context = context
    session.save(update_fields=("context", "updated_at"))


def _sse_data(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False, default=str)}\n\n"


_ASSISTANT_STREAM_END = object()
_ASSISTANT_STREAM_EVENT = "event"
_ASSISTANT_STREAM_ERROR = "error"
_ASSISTANT_STREAM_SLOTS = threading.BoundedSemaphore(
    value=max(1, int(settings.AI_ASSISTANT_STREAM_WORKERS))
)


async def _assistant_event_stream(
    *,
    session: ChatSession,
    message: str,
    user: Any,
) -> AsyncIterator[str]:
    """Stream a synchronous assistant safely from Django's ASGI handler.

    Django has to fully consume synchronous StreamingHttpResponse iterators when
    serving ASGI. Advancing the assistant in worker threads keeps the response
    genuinely incremental, while comments prevent idle proxy timeouts during a
    slow provider call or retry.
    """
    yield _sse_data({"type": "conversation", "conversation_id": str(session.pk)})

    if not _ASSISTANT_STREAM_SLOTS.acquire(blocking=False):
        yield _sse_data(
            {
                "type": "error",
                "code": "assistant_busy",
                "text": "Trợ lý đang xử lý nhiều yêu cầu. Vui lòng thử lại sau ít phút.",
            }
        )
        return

    heartbeat_seconds = max(
        0.05,
        float(getattr(settings, "AI_ASSISTANT_HEARTBEAT_SECONDS", 10.0)),
    )
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue[tuple[str, Any]] = asyncio.Queue()
    stopped = threading.Event()
    producer = threading.Thread(
        target=_produce_assistant_events,
        kwargs={
            "loop": loop,
            "queue": queue,
            "stopped": stopped,
            "session": session,
            "message": message,
            "user": user,
        },
        name="ai-assistant-stream",
        daemon=True,
    )
    try:
        producer.start()
    except RuntimeError:
        _ASSISTANT_STREAM_SLOTS.release()
        raise
    try:
        while True:
            try:
                kind, value = await asyncio.wait_for(
                    queue.get(),
                    timeout=heartbeat_seconds,
                )
            except TimeoutError:
                yield ": keep-alive\n\n"
                continue

            if value is _ASSISTANT_STREAM_END:
                break
            if kind == _ASSISTANT_STREAM_ERROR:
                raise value
            yield _sse_data(value.to_dict())
    finally:
        stopped.set()


def _produce_assistant_events(
    *,
    loop: asyncio.AbstractEventLoop,
    queue: asyncio.Queue[tuple[str, Any]],
    stopped: threading.Event,
    session: ChatSession,
    message: str,
    user: Any,
) -> None:
    try:
        for event in ShoppingAssistant().handle_turn(
            session=session,
            user_text=message,
            user=user,
        ):
            if stopped.is_set():
                break
            _enqueue_stream_item(loop, queue, (_ASSISTANT_STREAM_EVENT, event))
    except Exception as exc:
        _enqueue_stream_item(loop, queue, (_ASSISTANT_STREAM_ERROR, exc))
    finally:
        connections.close_all()
        _ASSISTANT_STREAM_SLOTS.release()
        _enqueue_stream_item(
            loop,
            queue,
            (_ASSISTANT_STREAM_EVENT, _ASSISTANT_STREAM_END),
        )


def _enqueue_stream_item(
    loop: asyncio.AbstractEventLoop,
    queue: asyncio.Queue[tuple[str, Any]],
    item: tuple[str, Any],
) -> None:
    try:
        loop.call_soon_threadsafe(queue.put_nowait, item)
    except RuntimeError:
        # The ASGI event loop can already be closed after a client disconnect.
        pass


class ProductAIReviewSummaryThrottle(AnonRateThrottle):
    scope = "ai_review_summary"

    def get_rate(self):
        rates = settings.REST_FRAMEWORK.get("DEFAULT_THROTTLE_RATES", {})
        return rates.get(self.scope, "10/minute")


class ProductAISummaryThrottle(AnonRateThrottle):
    scope = "ai_product_summary"

    def get_rate(self):
        rates = settings.REST_FRAMEWORK.get("DEFAULT_THROTTLE_RATES", {})
        return rates.get(self.scope, "10/minute")


class ProductCompareThrottle(AnonRateThrottle):
    scope = "ai_product_compare"

    def get_rate(self):
        rates = settings.REST_FRAMEWORK.get("DEFAULT_THROTTLE_RATES", {})
        return rates.get(self.scope, "10/minute")


class SellerListingThrottle(UserRateThrottle):
    scope = "ai_seller_listing"

    def get_rate(self):
        rates = settings.REST_FRAMEWORK.get("DEFAULT_THROTTLE_RATES", {})
        return rates.get(self.scope, "10/minute")


class ProductAIReviewSummaryView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ProductAIReviewSummaryThrottle]

    @extend_schema(
        operation_id="ai_product_review_summary",
        responses={200: ProductAIReviewSummaryResponseSerializer},
    )
    def get(self, request, product_id):
        product = get_object_or_404(ProductSelector.public_base(), pk=product_id)
        data = AIService().summarize_product_reviews(product.pk, user=request.user)
        return success_response(data=data)


class ProductAISummaryView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ProductAISummaryThrottle]

    @extend_schema(
        operation_id="ai_product_summary",
        responses={200: ProductAISummaryResponseSerializer},
    )
    def get(self, request, product_id):
        product = get_object_or_404(ProductSelector.public_base(), pk=product_id)
        data = AIService().summarize_product_details(product.pk, user=request.user)
        return success_response(data=data)


class ProductCompareView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ProductCompareThrottle]

    @extend_schema(
        operation_id="ai_product_compare",
        request=ProductCompareRequestSerializer,
        responses={200: ProductCompareResponseSerializer},
    )
    def post(self, request):
        serializer = ProductCompareRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = AIService().compare_products(
            serializer.validated_data["product_ids"], user=request.user
        )
        return success_response(data=data)


class SellerListingGenerateView(APIView):
    permission_classes = [IsSeller]
    throttle_classes = [SellerListingThrottle]

    @extend_schema(
        operation_id="ai_seller_product_listing",
        request=SellerListingRequestSerializer,
        responses={200: SellerListingResponseSerializer},
    )
    def post(self, request):
        serializer = SellerListingRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = AIService().generate_product_listing(
            name=serializer.validated_data["name"],
            keywords=serializer.validated_data["keywords"],
            user=request.user,
        )
        return success_response(data=data)


class BaseAISearchView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    throttle_classes = [AISearchRateThrottle]

    def _response_for(self, outcome):
        page = self.paginate_queryset(outcome.products)
        data = {
            "results": PublicProductListSerializer(
                page,
                many=True,
                context=self.get_serializer_context(),
            ).data,
            "explanation": outcome.explanation,
            "intent": outcome.intent,
            "ai_used": outcome.ai_used,
            "fallback_used": outcome.fallback_used,
            "match_reasons": outcome.match_reasons,
        }
        return self.get_paginated_response(data)


class SmartSearchView(BaseAISearchView):
    serializer_class = SmartSearchQuerySerializer

    @extend_schema(
        operation_id="ai_smart_search",
        parameters=[SmartSearchQuerySerializer],
        responses={200: AISearchResponseSerializer},
    )
    def get(self, request):
        query = self.get_serializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        params = dict(query.validated_data)
        query_text = params.pop("q")
        params.pop("page", None)
        params.pop("page_size", None)
        outcome = AISearchService.smart_search(
            query=query_text,
            user=request.user if request.user.is_authenticated else None,
            filters=params,
        )
        return self._response_for(outcome)


class SemanticSearchView(BaseAISearchView):
    serializer_class = SemanticSearchQuerySerializer

    @extend_schema(
        operation_id="ai_semantic_search",
        parameters=[SemanticSearchQuerySerializer],
        responses={200: AISearchResponseSerializer},
    )
    def get(self, request):
        query = self.get_serializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        params = dict(query.validated_data)
        query_text = params.pop("q")
        params.pop("page", None)
        params.pop("page_size", None)
        outcome = AISearchService.semantic_search(
            query=query_text,
            user=request.user if request.user.is_authenticated else None,
            filters=params,
        )
        return self._response_for(outcome)
