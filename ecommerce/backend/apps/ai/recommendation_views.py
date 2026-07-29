from django.http import Http404
from drf_spectacular.utils import extend_schema
from rest_framework import generics
from rest_framework.permissions import AllowAny

from apps.product.models import Product
from apps.product.selectors import ProductSelector
from apps.product.serializers import PublicProductListSerializer

from .permissions import AISearchRateThrottle
from .recommendation_service import RecommendationService
from .serializers import (
    RecommendationQuerySerializer,
    RecommendationResponseSerializer,
    SimilarProductsQuerySerializer,
)


class BaseRecommendationView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    throttle_classes = [AISearchRateThrottle]

    def _validated_params(self, request) -> dict:
        query = self.get_serializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        return dict(query.validated_data)

    def _response_for(self, outcome):
        page = self.paginate_queryset(outcome.products)
        data = {
            "results": PublicProductListSerializer(
                page,
                many=True,
                context=self.get_serializer_context(),
            ).data,
            "ai_used": outcome.ai_used,
            "fallback_used": outcome.fallback_used,
            "personalized": outcome.personalized,
            "strategy": outcome.strategy,
        }
        return self.get_paginated_response(data)

    @staticmethod
    def _public_source(product_id) -> Product:
        product = (
            ProductSelector.public_base()
            .select_related("category", "brand")
            .filter(pk=product_id)
            .first()
        )
        if product is None:
            raise Http404
        return product

    @staticmethod
    def _request_user(request):
        return request.user if request.user.is_authenticated else None


class ProductRecommendationsView(BaseRecommendationView):
    serializer_class = RecommendationQuerySerializer

    @extend_schema(
        operation_id="product_recommendations",
        parameters=[RecommendationQuerySerializer],
        responses={200: RecommendationResponseSerializer},
    )
    def get(self, request, product_id):
        params = self._validated_params(request)
        outcome = RecommendationService.recommendations(
            context_product=self._public_source(product_id),
            browsing_ids=params["browsing_history"],
            user=self._request_user(request),
        )
        return self._response_for(outcome)


class SimilarProductsView(BaseRecommendationView):
    serializer_class = SimilarProductsQuerySerializer

    @extend_schema(
        operation_id="product_similar",
        parameters=[SimilarProductsQuerySerializer],
        responses={200: RecommendationResponseSerializer},
    )
    def get(self, request, product_id):
        params = self._validated_params(request)
        params.pop("page", None)
        params.pop("page_size", None)
        outcome = RecommendationService.similar_products(
            context_product=self._public_source(product_id),
        )
        return self._response_for(outcome)


class HomeRecommendationsView(BaseRecommendationView):
    serializer_class = RecommendationQuerySerializer

    @extend_schema(
        operation_id="ai_recommendations",
        parameters=[RecommendationQuerySerializer],
        responses={200: RecommendationResponseSerializer},
    )
    def get(self, request):
        params = self._validated_params(request)
        outcome = RecommendationService.recommendations(
            browsing_ids=params["browsing_history"],
            user=self._request_user(request),
        )
        return self._response_for(outcome)
