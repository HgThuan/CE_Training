from typing import Any

from rest_framework.response import Response


def success_response(
    *,
    data: Any = None,
    message: str = "Thành công",
    meta: dict | None = None,
    status_code: int = 200,
) -> Response:
    payload: dict[str, Any] = {"success": True, "message": message, "data": data}
    if meta is not None:
        payload["meta"] = meta
    return Response(payload, status=status_code)


def error_response(
    *,
    message: str = "Có lỗi xảy ra",
    errors: dict | None = None,
    status_code: int = 400,
) -> Response:
    return Response(
        {"success": False, "message": message, "errors": errors or {}},
        status=status_code,
    )
