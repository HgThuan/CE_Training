from drf_spectacular.utils import extend_schema
from rest_framework import generics
from rest_framework.permissions import AllowAny

from apps.product.serializers import PublicProductListSerializer

from .permissions import AISearchRateThrottle
from .search_service import AISearchService
from .serializers import (
    AISearchResponseSerializer,
    SemanticSearchQuerySerializer,
    SmartSearchQuerySerializer,
)


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
