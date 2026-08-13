import os

from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")

django_asgi_application = get_asgi_application()

from apps.chat.auth import JWTAuthMiddleware  # noqa: E402
from apps.chat.routing import websocket_urlpatterns as chat_websocket_urlpatterns  # noqa: E402
from apps.notification.routing import (  # noqa: E402
    websocket_urlpatterns as notification_websocket_urlpatterns,
)

application = ProtocolTypeRouter(
    {
        "http": django_asgi_application,
        "websocket": JWTAuthMiddleware(
            URLRouter(chat_websocket_urlpatterns + notification_websocket_urlpatterns)
        ),
    }
)
