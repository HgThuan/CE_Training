import json

from django.conf import settings
from django.db import transaction
from django.http import StreamingHttpResponse
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
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

from .chat_service import AIChatService
from .models import ChatMessage, ChatSession
from .permissions import AISearchRateThrottle
from .renderers import ServerSentEventRenderer
from .search_service import AISearchService
from .serializers import (
    AISearchResponseSerializer,
    ChatMessageHistoryResponseSerializer,
    ChatTurnRequestSerializer,
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


class ChatSessionThrottle(SimpleRateThrottle):
    scope = "ai_chat_session"

    def get_rate(self):
        rates = settings.REST_FRAMEWORK.get("DEFAULT_THROTTLE_RATES", {})
        return rates.get(self.scope, "12/minute")

    def get_cache_key(self, request, view):
        session_id = request.data.get("session_id")
        guest_token = request.data.get("guest_token")
        if session_id:
            ident = f"session:{session_id}"
        elif guest_token:
            ident = f"guest:{guest_token}"
        elif request.user.is_authenticated:
            ident = f"user:{request.user.pk}"
        else:
            ident = self.get_ident(request)
        return self.cache_format % {"scope": self.scope, "ident": ident}


class ChatTurnView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ChatSessionThrottle]
    renderer_classes = [ServerSentEventRenderer, JSONRenderer]

    @extend_schema(
        operation_id="ai_shopping_chat_turn",
        request=ChatTurnRequestSerializer,
        responses={(200, "text/event-stream"): str},
    )
    def post(self, request):
        serializer = ChatTurnRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        session = _resolve_or_create_chat_session(request, serializer.validated_data)
        message = serializer.validated_data["message"]

        def event_stream():
            yield _sse_data({"type": "session", "session_id": str(session.pk)})
            for event in AIChatService().handle_turn(session, message):
                yield _sse_data(event.to_dict())

        response = StreamingHttpResponse(
            event_stream(),
            content_type="text/event-stream; charset=utf-8",
        )
        response["Cache-Control"] = "no-cache, no-transform"
        response["X-Accel-Buffering"] = "no"
        return response


class ChatMessageHistoryView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        operation_id="ai_shopping_chat_history",
        parameters=[
            OpenApiParameter(
                name="guest_token",
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Stable browser token required when the session is not user-owned.",
            )
        ],
        responses={200: ChatMessageHistoryResponseSerializer},
    )
    def get(self, request, session_id):
        guest_token = str(request.query_params.get("guest_token", "")).strip()
        session = _owned_chat_session(request, session_id, guest_token=guest_token)
        messages = session.messages.filter(
            role__in=(ChatMessage.Role.USER, ChatMessage.Role.ASSISTANT)
        ).order_by("created_at", "id")
        data = [AIChatService.serialize_message(message) for message in messages]
        return success_response(data=data)


def _resolve_or_create_chat_session(request, data) -> ChatSession:
    session_id = data.get("session_id")
    guest_token = str(data.get("guest_token", "")).strip()
    if session_id:
        if request.user.is_authenticated:
            session = ChatSession.objects.filter(pk=session_id, user=request.user).first()
            if session is not None:
                return session
            if guest_token:
                with transaction.atomic():
                    claimable = (
                        ChatSession.objects.select_for_update()
                        .filter(
                            pk=session_id,
                            user__isnull=True,
                            guest_token=guest_token,
                        )
                        .first()
                    )
                    if claimable is not None:
                        claimable.user = request.user
                        claimable.save(update_fields=("user", "updated_at"))
                        return claimable
            return get_object_or_404(ChatSession, pk=session_id, user=request.user)
        if not guest_token:
            raise ValidationError({"guest_token": ["guest_token là bắt buộc với khách."]})
        return get_object_or_404(
            ChatSession,
            pk=session_id,
            user__isnull=True,
            guest_token=guest_token,
        )

    if request.user.is_authenticated:
        return ChatSession.objects.create(
            user=request.user,
            guest_token=guest_token or None,
        )
    if not guest_token:
        raise ValidationError({"guest_token": ["guest_token là bắt buộc với khách."]})
    return ChatSession.objects.create(guest_token=guest_token)


def _owned_chat_session(request, session_id, *, guest_token: str) -> ChatSession:
    if request.user.is_authenticated:
        session = ChatSession.objects.filter(pk=session_id, user=request.user).first()
        if session is not None:
            return session
        if guest_token:
            return get_object_or_404(
                ChatSession,
                pk=session_id,
                user__isnull=True,
                guest_token=guest_token,
            )
        return get_object_or_404(ChatSession, pk=session_id, user=request.user)
    if not guest_token:
        raise ValidationError({"guest_token": ["guest_token là bắt buộc với khách."]})
    return get_object_or_404(
        ChatSession,
        pk=session_id,
        user__isnull=True,
        guest_token=guest_token,
    )


def _sse_data(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False, default=str)}\n\n"


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
