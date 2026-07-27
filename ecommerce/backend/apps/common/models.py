from django.conf import settings
from django.db import models


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
