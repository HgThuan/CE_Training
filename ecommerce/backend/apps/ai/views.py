from django.conf import settings
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import generics
from rest_framework.permissions import AllowAny
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle
from rest_framework.views import APIView

from apps.account.permissions import IsSeller
from apps.common.responses import success_response
from apps.product.selectors import ProductSelector
from apps.product.serializers import PublicProductListSerializer

from .permissions import AISearchRateThrottle
from .search_service import AISearchService
from .serializers import (
    AISearchResponseSerializer,
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
