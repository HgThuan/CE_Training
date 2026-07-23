import logging

from rest_framework.views import exception_handler as drf_exception_handler

from .exceptions import BusinessError
from .responses import error_response

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    if isinstance(exc, BusinessError):
        return error_response(
            message=str(exc),
            errors=exc.errors,
            status_code=exc.http_status,
        )

    response = drf_exception_handler(exc, context)
    if response is not None:
        default_messages = {
            400: "Dữ liệu không hợp lệ",
            401: "Vui lòng đăng nhập",
            403: "Bạn không có quyền thực hiện thao tác này",
            404: "Không tìm thấy dữ liệu",
            405: "Phương thức không được hỗ trợ",
            429: "Bạn đã gửi quá nhiều yêu cầu",
        }
        return error_response(
            message=default_messages.get(response.status_code, "Yêu cầu không hợp lệ"),
            errors=response.data,
            status_code=response.status_code,
        )

    request = context.get("request")
    logger.exception(
        "Unhandled exception",
        extra={
            "request_id": getattr(request, "request_id", "-"),
            "user_id": getattr(getattr(request, "user", None), "id", "-"),
        },
    )
    return error_response(message="Đã có lỗi hệ thống xảy ra", status_code=500)
