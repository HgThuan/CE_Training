from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import AccessToken

from apps.account.models import User


@database_sync_to_async
def _get_user(token_value: str):
    try:
        token = AccessToken(token_value)
        user = User.objects.get(pk=token["user_id"], is_active=True, is_deleted=False)
        if token.get("token_version") != user.token_version:
            return AnonymousUser()
        return user
    except (InvalidToken, TokenError, User.DoesNotExist, KeyError):
        return AnonymousUser()


class JWTAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        query = parse_qs(scope.get("query_string", b"").decode())
        token = (query.get("token") or [None])[0]
        if token is None:
            protocols = scope.get("subprotocols", [])
            token = protocols[1] if len(protocols) > 1 and protocols[0] == "jwt" else None
        scope["user"] = await _get_user(token) if token else AnonymousUser()
        return await super().__call__(scope, receive, send)
