from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.account.views import seller_document_download
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
    path("api/v1/", include("apps.product.urls")),
    path("api/v1/", include("apps.inventory.urls")),
    path("api/v1/", include("apps.storefront.urls")),
    path(
        "protected-media/seller-documents/<str:token>/",
        seller_document_download,
        name="seller-document-download",
    ),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
