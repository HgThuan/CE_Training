from django.urls import path

from .recommendation_views import HomeRecommendationsView, RecommendationEventView
from .views import (
    ProductAIReviewSummaryView,
    ProductAISummaryView,
    SemanticSearchView,
    SmartSearchView,
)

app_name = "ai"

urlpatterns = [
    path("smart-search/", SmartSearchView.as_view(), name="smart-search"),
    path("semantic-search/", SemanticSearchView.as_view(), name="semantic-search"),
    path(
        "products/<uuid:product_id>/ai-review-summary",
        ProductAIReviewSummaryView.as_view(),
        name="product-review-summary",
    ),
    path(
        "products/<uuid:product_id>/ai-summary",
        ProductAISummaryView.as_view(),
        name="product-summary",
    ),
    path(
        "recommendations/",
        HomeRecommendationsView.as_view(),
        name="recommendations",
    ),
    path(
        "recommendation-events/",
        RecommendationEventView.as_view(),
        name="recommendation-event",
    ),
]
