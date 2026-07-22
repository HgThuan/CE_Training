import logging

from django.core.cache import cache
from django.db import connection
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from .responses import error_response, success_response
from .serializers import HealthCheckErrorResponseSerializer, HealthCheckSuccessResponseSerializer

logger = logging.getLogger(__name__)


class HealthCheckView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        responses={
            200: HealthCheckSuccessResponseSerializer,
            503: HealthCheckErrorResponseSerializer,
        }
    )
    def get(self, request):
        checks: dict[str, str] = {}

        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            checks["database"] = "ok"
        except Exception:
            logger.exception("Database health check failed")
            checks["database"] = "error"

        try:
            cache.set("healthcheck", "ok", timeout=10)
            checks["cache"] = "ok" if cache.get("healthcheck") == "ok" else "error"
        except Exception:
            logger.exception("Cache health check failed")
            checks["cache"] = "error"

        if all(result == "ok" for result in checks.values()):
            return success_response(
                message="Dịch vụ hoạt động bình thường",
                data={"status": "healthy", "checks": checks},
            )

        return error_response(
            message="Dịch vụ chưa sẵn sàng",
            errors={"status": "unhealthy", "checks": checks},
            status_code=503,
        )
