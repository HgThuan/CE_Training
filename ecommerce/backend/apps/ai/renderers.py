from rest_framework.renderers import JSONRenderer


class ServerSentEventRenderer(JSONRenderer):
    """Negotiate SSE responses while keeping pre-stream errors JSON serializable."""

    media_type = "text/event-stream"
    format = "sse"
