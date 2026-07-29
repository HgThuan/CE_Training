from django.urls import path

from .customer_views import ShopFollowToggleView, WishlistListView, WishlistToggleView
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
    path(
        "wishlist/",
        WishlistListView.as_view(),
        name="wishlist-list",
    ),
    path(
        "wishlist/toggle/",
        WishlistToggleView.as_view(),
        name="wishlist-toggle",
    ),
    path(
        "shops/<int:shop_id>/follow/",
        ShopFollowToggleView.as_view(),
        name="shop-follow-toggle",
    ),
]
