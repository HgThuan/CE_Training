from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication

from apps.common.logging import request_context


class VersionedJWTAuthentication(JWTAuthentication):
    """Reject access tokens issued before a security-sensitive account change."""

    def get_user(self, validated_token):
        user = super().get_user(validated_token)
        token_version = validated_token.get("token_version")
        if token_version is None or token_version != user.token_version:
            raise AuthenticationFailed(
                "Phiên đăng nhập không còn hiệu lực",
                code="session_revoked",
            )
        context = request_context.get()
        if context is not None:
            request_context.set({**context, "user_id": user.pk})
        return user
