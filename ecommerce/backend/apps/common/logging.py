import json
import logging
from contextvars import ContextVar
from datetime import UTC, datetime

request_context = ContextVar("request_context", default=None)


class RequestContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        context = request_context.get() or {}
        for key in ("request_id", "user_id", "path", "method"):
            if not hasattr(record, key):
                setattr(record, key, context.get(key, "-"))
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
            "user_id": str(getattr(record, "user_id", "-")),
            "path": getattr(record, "path", "-"),
            "method": getattr(record, "method", "-"),
        }
        for key in ("status_code", "duration_ms", "event", "cache_key"):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)
