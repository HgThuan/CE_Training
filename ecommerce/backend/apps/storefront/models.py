import uuid

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from apps.common.models import TimeStampedModel


class Banner(TimeStampedModel):
    class Position(models.TextChoices):
        HERO = "hero", "Hero"
        MIDDLE = "middle", "Giữa trang"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=180, blank=True)
    image_url = models.TextField()
    target_url = models.TextField(blank=True)
    position = models.CharField(
        max_length=30,
        choices=Position.choices,
        default=Position.HERO,
        db_index=True,
    )
    sort_order = models.IntegerField(default=0)
    starts_at = models.DateTimeField(null=True, blank=True, db_index=True)
    ends_at = models.DateTimeField(null=True, blank=True, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("position", "sort_order", "created_at", "id")
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(starts_at__isnull=True)
                    | Q(ends_at__isnull=True)
                    | Q(ends_at__gt=models.F("starts_at"))
                ),
                name="banner_schedule_valid",
            ),
        ]
        indexes = [
            models.Index(
                fields=("position", "is_active", "is_deleted", "sort_order"),
                name="banner_public_order_idx",
            ),
        ]

    def clean(self) -> None:
        super().clean()
        if self.starts_at and self.ends_at and self.ends_at <= self.starts_at:
            raise ValidationError({"ends_at": "Thời gian kết thúc phải sau thời gian bắt đầu"})

    def __str__(self) -> str:
        return self.title or str(self.pk)
