from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import signing
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from apps.common.exceptions import BusinessError

User = get_user_model()


class EmailVerificationTokenService:
    salt = "account.email-verification"

    @classmethod
    def generate(cls, user) -> str:
        return signing.dumps(
            {"user_id": user.pk, "email": user.email},
            salt=cls.salt,
            compress=True,
        )

    @classmethod
    def resolve(cls, token: str):
        try:
            payload = signing.loads(
                token,
                salt=cls.salt,
                max_age=settings.EMAIL_VERIFICATION_TOKEN_MAX_AGE,
            )
        except signing.SignatureExpired as exc:
            raise BusinessError(
                "Liên kết xác thực email đã hết hạn",
                errors={"token": ["Vui lòng yêu cầu gửi lại email xác thực"]},
            ) from exc
        except signing.BadSignature as exc:
            raise BusinessError(
                "Liên kết xác thực email không hợp lệ",
                errors={"token": ["Token không hợp lệ"]},
            ) from exc

        user = User.objects.filter(pk=payload.get("user_id"), email=payload.get("email")).first()
        if user is None:
            raise BusinessError(
                "Liên kết xác thực email không hợp lệ",
                errors={"token": ["Không tìm thấy tài khoản"]},
            )
        return user


class AuthTokenService:
    @staticmethod
    def issue_pair(user) -> dict[str, str]:
        if not user.is_active:
            raise AuthenticationFailed("Tài khoản đã bị khóa")

        refresh = RefreshToken.for_user(user)
        refresh["role"] = user.role
        refresh["token_version"] = user.token_version
        return {"access": str(refresh.access_token), "refresh": str(refresh)}


class VersionedTokenRefreshSerializer(TokenRefreshSerializer):
    def validate(self, attrs):
        try:
            token = self.token_class(attrs["refresh"])
        except TokenError as exc:
            raise BusinessError(
                "Refresh token không hợp lệ hoặc đã bị thu hồi",
                errors={"refresh": ["Phiên đăng nhập không còn hiệu lực"]},
                http_status=401,
            ) from exc
        user = User.objects.filter(pk=token.get("user_id")).first()
        if user is None or not user.is_active:
            raise BusinessError("Tài khoản không còn hoạt động", http_status=401)
        if token.get("token_version") != user.token_version:
            raise BusinessError("Phiên đăng nhập không còn hiệu lực", http_status=401)

        data = super().validate(attrs)
        return data
