from django.http import Http404
from django.utils.crypto import salted_hmac
from drf_spectacular.utils import extend_schema
from rest_framework import generics
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from apps.common.responses import success_response
from apps.product.models import Product
from apps.product.selectors import ProductSelector
from apps.product.serializers import PublicProductListSerializer

from .models import RecommendationEvent
from .permissions import AIRecommendationRateThrottle, RecommendationEventRateThrottle
from .recommendation_service import RecommendationService
from .serializers import (
    RecommendationEventSerializer,
    RecommendationQuerySerializer,
    RecommendationResponseSerializer,
    SimilarProductsQuerySerializer,
)


class BaseRecommendationView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    throttle_classes = [AIRecommendationRateThrottle]

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
            "recommendation_id": outcome.recommendation_id,
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
        service_params = {
            "context_product": self._public_source(product_id),
            "browsing_ids": params["browsing_history"],
            "user": self._request_user(request),
        }
        if params["cart_products"]:
            service_params["cart_ids"] = params["cart_products"]
        if params["landing_context"] != "home":
            service_params["landing_context"] = params["landing_context"]
        if params["traffic_source"] != "direct":
            service_params["traffic_source"] = params["traffic_source"]
        outcome = RecommendationService.recommendations(
            **service_params,
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
        service_params = {
            "browsing_ids": params["browsing_history"],
            "user": self._request_user(request),
        }
        if params["cart_products"]:
            service_params["cart_ids"] = params["cart_products"]
        if params["landing_context"] != "home":
            service_params["landing_context"] = params["landing_context"]
        if params["traffic_source"] != "direct":
            service_params["traffic_source"] = params["traffic_source"]
        outcome = RecommendationService.recommendations(**service_params)
        return self._response_for(outcome)


class RecommendationEventView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [RecommendationEventRateThrottle]

    @extend_schema(
        operation_id="recommendation_event",
        request=RecommendationEventSerializer,
        responses={200: RecommendationEventSerializer},
    )
    def post(self, request):
        serializer = RecommendationEventSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        product = ProductSelector.public_base().filter(pk=data["product_id"]).first()
        if product is None:
            raise Http404
        visitor_id = data.get("visitor_id", "")
        event = RecommendationEvent.objects.create(
            recommendation_id=data["recommendation_id"],
            user=request.user if request.user.is_authenticated else None,
            visitor_id_hash=(
                salted_hmac("recommendation-visitor", visitor_id).hexdigest()
                if visitor_id
                else ""
            ),
            product=product,
            event_type=data["event_type"],
            source=data["source"],
            position=data.get("position"),
            context=data.get("context", {}),
        )
        return success_response(data={"id": str(event.pk)}, message="Đã ghi nhận tín hiệu.")
