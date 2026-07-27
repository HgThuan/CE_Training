import uuid

from django.db import models
from django.db.models import F, Q
from django.db.models.functions import Lower

from apps.common.models import TimeStampedModel


class Category(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    parent = models.ForeignKey(
        "self",
        on_delete=models.RESTRICT,
        related_name="children",
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=180, unique=True)
    image_url = models.TextField(null=True, blank=True)
    sort_order = models.IntegerField(default=0, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("sort_order", "name", "id")
        constraints = [
            models.CheckConstraint(
                condition=~Q(id=F("parent_id")),
                name="catalog_category_not_self_parent",
            ),
        ]
        indexes = [
            models.Index(
                fields=["parent", "sort_order"],
                name="catalog_cat_parent_sort_idx",
            ),
            models.Index(
                fields=["is_active", "is_deleted", "sort_order"],
                name="catalog_cat_public_idx",
            ),
            models.Index(fields=["created_at"], name="catalog_cat_created_idx"),
        ]

    def __str__(self) -> str:
        return self.name


class Brand(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=150, unique=True)
    slug = models.SlugField(max_length=180, unique=True)
    logo_url = models.TextField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("name", "id")
        constraints = [
            models.UniqueConstraint(
                Lower("name"),
                name="catalog_brand_name_ci_unique",
            ),
        ]
        indexes = [
            models.Index(
                fields=["is_active", "is_deleted", "name"],
                name="catalog_brand_public_idx",
            ),
            models.Index(fields=["created_at"], name="catalog_brand_created_idx"),
        ]

    def __str__(self) -> str:
        return self.name
