from django.urls import path

from .views import ProductAnswerCreateView, ProductQuestionListCreateView

app_name = "engagement"

urlpatterns = [
    path(
        "products/<uuid:product_id>/questions/",
        ProductQuestionListCreateView.as_view(),
        name="product-question-list",
    ),
    path(
        "questions/<uuid:question_id>/answers/",
        ProductAnswerCreateView.as_view(),
        name="product-answer-create",
    ),
]
