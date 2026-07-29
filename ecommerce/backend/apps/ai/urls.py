from django.urls import path

from .recommendation_views import HomeRecommendationsView
from .views import SemanticSearchView, SmartSearchView

app_name = "ai"

urlpatterns = [
    path("smart-search/", SmartSearchView.as_view(), name="smart-search"),
    path("semantic-search/", SemanticSearchView.as_view(), name="semantic-search"),
    path(
        "recommendations/",
        HomeRecommendationsView.as_view(),
        name="recommendations",
    ),
]
