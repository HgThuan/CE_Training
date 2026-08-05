import logging
import time
import uuid

from .logging import request_context

logger = logging.getLogger("http.request")


class RequestIdMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        started = time.monotonic()
        request.request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        user = getattr(request, "user", None)
        token = request_context.set(
            {
                "request_id": request.request_id,
                "user_id": getattr(user, "pk", "-")
                if getattr(user, "is_authenticated", False)
                else "-",
                "path": request.path,
                "method": request.method,
            }
        )
        try:
            response = self.get_response(request)
            response["X-Request-ID"] = request.request_id
            logger.info(
                "request.completed",
                extra={
                    "status_code": response.status_code,
                    "duration_ms": round((time.monotonic() - started) * 1000, 2),
                },
            )
            return response
        finally:
            request_context.reset(token)
