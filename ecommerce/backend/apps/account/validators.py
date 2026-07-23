from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers


def validate_new_password(password: str, *, user=None) -> str:
    try:
        validate_password(password, user=user)
    except DjangoValidationError as exc:
        raise serializers.ValidationError(list(exc.messages)) from exc
    return password


def validate_matching_passwords(attrs: dict, *, password_field: str = "password") -> dict:
    confirmation_field = f"{password_field}_confirm"
    if attrs.get(password_field) != attrs.get(confirmation_field):
        raise serializers.ValidationError(
            {confirmation_field: ["Mật khẩu xác nhận không khớp"]},
        )
    return attrs
