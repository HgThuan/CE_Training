import uuid
from typing import Any

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

_SITE_SETTING_CACHE_MISSING = object()


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class AuditLog(TimeStampedModel):
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="audit_logs",
    )
    action = models.CharField(max_length=100)
    target_type = models.CharField(max_length=50)
    # Generic audit targets use both integer IDs (account/shop) and UUIDs
    # (catalog/product), so the storage type must support both identifiers.
    target_id = models.CharField(max_length=64)
    reason = models.TextField(blank=True)
    request_id = models.CharField(max_length=64, blank=True, db_index=True)
    diff = models.JSONField(default=dict)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["actor", "created_at"], name="audit_actor_created_idx"),
            models.Index(
                fields=["target_type", "target_id", "created_at"],
                name="audit_target_created_idx",
            ),
        ]


class SiteSetting(TimeStampedModel):
    class ValueType(models.TextChoices):
        STRING = "string", "String"
        NUMBER = "number", "Number"
        BOOLEAN = "boolean", "Boolean"
        JSON = "json", "JSON"

    CACHE_TTL_SECONDS = 5 * 60
    CACHE_NAMESPACE = "site-setting"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    key = models.CharField(max_length=120, unique=True)
    value = models.JSONField()
    value_type = models.CharField(
        max_length=20,
        choices=ValueType.choices,
        default=ValueType.JSON,
    )
    description = models.TextField(blank=True)
    is_public = models.BooleanField(default=False)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="updated_site_settings",
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ("key",)

    @classmethod
    def cache_key(cls, key: str) -> str:
        from apps.common.cache_utils import build_cache_key

        return build_cache_key(cls.CACHE_NAMESPACE, {"key": key.strip()})

    @classmethod
    def get_value(cls, key: str, default: Any = None) -> Any:
        from apps.common.cache_utils import safe_cache_get, safe_cache_set

        normalized_key = key.strip()
        if not normalized_key:
            return default
        cache_key = cls.cache_key(normalized_key)
        cached = safe_cache_get(cache_key, _SITE_SETTING_CACHE_MISSING)
        if cached is not _SITE_SETTING_CACHE_MISSING:
            if isinstance(cached, dict) and cached.get("_site_setting_exists") is True:
                return cached.get("value")
            if isinstance(cached, dict) and cached.get("_site_setting_exists") is False:
                return default

        try:
            value = cls.objects.only("value").get(key=normalized_key).value
        except cls.DoesNotExist:
            safe_cache_set(
                cache_key,
                {"_site_setting_exists": False},
                timeout=cls.CACHE_TTL_SECONDS,
            )
            return default
        safe_cache_set(
            cache_key,
            {"_site_setting_exists": True, "value": value},
            timeout=cls.CACHE_TTL_SECONDS,
        )
        return value

    @classmethod
    def get_bool(cls, key: str, default: bool = False) -> bool:
        value = cls.get_value(key, default)
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)) and value in {0, 1}:
            return bool(value)
        if isinstance(value, str):
            normalized = value.strip().casefold()
            if normalized in {"1", "true", "yes", "on", "enabled"}:
                return True
            if normalized in {"0", "false", "no", "off", "disabled"}:
                return False
        return default

    @classmethod
    def set_value(
        cls,
        key: str,
        value: Any,
        *,
        description: str | None = None,
        is_public: bool | None = None,
        updated_by: Any = None,
    ) -> "SiteSetting":
        normalized_key = key.strip()
        if not normalized_key:
            raise ValueError("Site setting key must not be empty")
        defaults: dict[str, Any] = {
            "value": value,
            "value_type": cls.infer_value_type(value),
            "updated_by": updated_by,
        }
        if description is not None:
            defaults["description"] = description
        if is_public is not None:
            defaults["is_public"] = is_public
        setting, _ = cls.objects.update_or_create(
            key=normalized_key,
            defaults=defaults,
        )
        return setting

    @classmethod
    def infer_value_type(cls, value: Any) -> str:
        if isinstance(value, bool):
            return cls.ValueType.BOOLEAN
        if isinstance(value, (int, float)):
            return cls.ValueType.NUMBER
        if isinstance(value, str):
            return cls.ValueType.STRING
        return cls.ValueType.JSON

    def clean(self) -> None:
        super().clean()
        expected_type = self.infer_value_type(self.value)
        if self.value_type != expected_type:
            raise ValidationError(
                {"value_type": (f"Value type must be '{expected_type}' for the stored JSON value.")}
            )

    def save(self, *args: Any, **kwargs: Any) -> None:
        from apps.common.cache_utils import (
            invalidate_cache_keys_on_commit,
            safe_cache_delete_many,
        )

        self.key = self.key.strip()
        previous_key = None
        if self.pk:
            previous_key = (
                type(self).objects.filter(pk=self.pk).values_list("key", flat=True).first()
            )
        super().save(*args, **kwargs)
        keys = tuple({self.cache_key(key) for key in (previous_key, self.key) if key})
        safe_cache_delete_many(*keys)
        invalidate_cache_keys_on_commit(*keys)

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        from apps.common.cache_utils import (
            invalidate_cache_keys_on_commit,
            safe_cache_delete,
        )

        cache_key = self.cache_key(self.key)
        result = super().delete(*args, **kwargs)
        safe_cache_delete(cache_key)
        invalidate_cache_keys_on_commit(cache_key)
        return result

    def __str__(self) -> str:
        return self.key
