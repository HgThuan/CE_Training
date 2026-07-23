from unittest.mock import MagicMock, patch

from rest_framework.test import APIClient


@patch("apps.common.views.cache")
@patch("apps.common.views.connection.cursor")
def test_health_check_returns_standard_success_response(mock_cursor, mock_cache):
    mock_cursor.return_value.__enter__.return_value.fetchone.return_value = (1,)
    mock_cache.get.return_value = "ok"

    response = APIClient().get("/api/health/")

    assert response.status_code == 200
    assert response.json() == {
        "success": True,
        "message": "Dịch vụ hoạt động bình thường",
        "data": {
            "status": "healthy",
            "checks": {"database": "ok", "cache": "ok"},
        },
    }


@patch("apps.common.views.cache")
@patch("apps.common.views.connection.cursor")
def test_health_check_returns_503_when_dependency_fails(mock_cursor, mock_cache):
    mock_cursor.side_effect = RuntimeError("database unavailable")
    mock_cache.get.return_value = "ok"
    mock_cache.set = MagicMock()

    response = APIClient().get("/api/health/")

    assert response.status_code == 503
    assert response.json()["success"] is False
    assert response.json()["errors"]["checks"]["database"] == "error"
