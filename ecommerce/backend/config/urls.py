from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.account.views import seller_document_download
from apps.ai.recommendation_views import (
    ProductRecommendationsView,
    SimilarProductsView,
)
from apps.ai.views import (
    ChatFeedbackView,
    ChatMessageHistoryView,
    ChatTurnView,
    ProductCompareView,
    SellerListingGenerateView,
)
from apps.common.views import HealthCheckView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", HealthCheckView.as_view(), name="health-check"),
    path("api/schema/", SpectacularAPIView.as_view(), name="api-schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="api-schema"),
        name="api-docs",
    ),
    path("api/v1/", include("apps.account.urls")),
    path("api/v1/", include("apps.catalog.urls")),
    path(
        "api/v1/products/<uuid:product_id>/recommendations/",
        ProductRecommendationsView.as_view(),
        name="product-recommendations",
    ),
    path(
        "api/v1/products/<uuid:product_id>/similar/",
        SimilarProductsView.as_view(),
        name="product-similar",
    ),
    path("api/v1/products/compare", ProductCompareView.as_view(), name="product-compare"),
    path("api/v1/chat/turn", ChatTurnView.as_view(), name="ai-shopping-chat-turn"),
    path(
        "api/v1/chat/messages/<uuid:message_id>/feedback",
        ChatFeedbackView.as_view(),
        name="ai-shopping-chat-feedback",
    ),
    path(
        "api/v1/chat/sessions/<uuid:session_id>/messages",
        ChatMessageHistoryView.as_view(),
        name="ai-shopping-chat-history",
    ),
    path(
        "api/v1/seller/products/generate-listing",
        SellerListingGenerateView.as_view(),
        name="seller-product-generate-listing",
    ),
    path("api/v1/", include("apps.product.urls")),
    path("api/v1/", include("apps.inventory.urls")),
    path("api/v1/", include("apps.storefront.urls")),
    path("api/v1/", include("apps.engagement.urls")),
    path("api/v1/cart/", include("apps.cart.urls")),
    path("api/v1/", include("apps.promotion.urls")),
    path("api/v1/", include("apps.order.urls")),
    path("api/v1/", include("apps.payment.urls")),
    path("api/v1/", include("apps.after_sales.urls")),
    path("api/v1/", include("apps.review.urls")),
    path("api/v1/", include("apps.chat.urls")),
    path("api/v1/", include("apps.notification.urls")),
    path("api/v1/", include("apps.report.urls")),
    path("api/v1/ai/", include("apps.ai.urls")),
    path(
        "protected-media/seller-documents/<str:token>/",
        seller_document_download,
        name="seller-document-download",
    ),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
