from django.urls import path

from .views import SemanticSearchView, SmartSearchView

app_name = "ai"

urlpatterns = [
    path("smart-search/", SmartSearchView.as_view(), name="smart-search"),
    path("semantic-search/", SemanticSearchView.as_view(), name="semantic-search"),
]
