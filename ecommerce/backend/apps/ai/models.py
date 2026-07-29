import re
import uuid
from decimal import Decimal
from typing import Any

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone
from pgvector.django import HnswIndex, VectorField

from apps.common.models import TimeStampedModel

EMBEDDING_DIMENSIONS = 1536
LOG_PROMPT_MAX_LENGTH = 4_000
LOG_RESPONSE_MAX_LENGTH = 8_000
LOG_ERROR_MAX_LENGTH = 2_000

SHA256_VALIDATOR = RegexValidator(
    regex=r"^[0-9a-f]{64}$",
    message="Content hash must be a lowercase SHA-256 digest.",
)
SECRET_ASSIGNMENT_RE = re.compile(
    r"(?i)\b(api[_-]?key|authorization|access[_-]?token|refresh[_-]?token|"
    r"bearer|password|secret)\b(\s*[:=]\s*|\s+)([^\s,;]+)"
)
BEARER_TOKEN_RE = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=\-]+")
KNOWN_SECRET_TOKEN_RE = re.compile(r"\b(?:AIza|sk-|AQ\.)[A-Za-z0-9._-]{16,}\b")
EMAIL_RE = re.compile(r"(?<![\w.+-])[\w.+-]+@[\w-]+(?:\.[\w-]+)+(?![\w.-])")
SENSITIVE_METADATA_KEY_RE = re.compile(
    r"(?i)(?:api.?key|authorization|password|secret|token|credential)"
)
TRUNCATION_MARKER = "…[truncated]"


def sanitize_ai_text(value: Any, *, max_length: int) -> str:
    if value is None:
        return ""
    text = str(value)
    text = BEARER_TOKEN_RE.sub("Bearer [REDACTED]", text)
    text = SECRET_ASSIGNMENT_RE.sub(
        lambda match: f"{match.group(1)}{match.group(2)}[REDACTED]",
        text,
    )
    text = KNOWN_SECRET_TOKEN_RE.sub("[REDACTED]", text)
    text = EMAIL_RE.sub("[REDACTED_EMAIL]", text)
    if len(text) <= max_length:
        return text
    keep_length = max(0, max_length - len(TRUNCATION_MARKER))
    return f"{text[:keep_length]}{TRUNCATION_MARKER}"


def sanitize_ai_payload(
    value: Any,
    *,
    depth: int = 0,
    max_depth: int = 4,
) -> Any:
    if depth >= max_depth:
        return "[TRUNCATED]"
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for index, (key, item) in enumerate(value.items()):
            if index >= 50:
                sanitized["_truncated"] = True
                break
            normalized_key = str(key)[:120]
            if SENSITIVE_METADATA_KEY_RE.search(normalized_key):
                sanitized[normalized_key] = "[REDACTED]"
            else:
                sanitized[normalized_key] = sanitize_ai_payload(
                    item,
                    depth=depth + 1,
                    max_depth=max_depth,
                )
        return sanitized
    if isinstance(value, (list, tuple)):
        return [
            sanitize_ai_payload(
                item,
                depth=depth + 1,
                max_depth=max_depth,
            )
            for item in value[:50]
        ]
    if isinstance(value, str):
        return sanitize_ai_text(value, max_length=1_000)
    return value


def generate_request_id() -> str:
    return str(uuid.uuid4())


class ProductEmbedding(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(
        "product.Product",
        on_delete=models.CASCADE,
        related_name="embeddings",
    )
    variant = models.ForeignKey(
        "product.ProductVariant",
        on_delete=models.CASCADE,
        related_name="embeddings",
        null=True,
        blank=True,
    )
    language_code = models.CharField(max_length=10, default="vi")
    model_name = models.CharField(max_length=120)
    model_version = models.CharField(max_length=80, blank=True)
    content_hash = models.CharField(
        max_length=64,
        validators=[SHA256_VALIDATOR],
    )
    embedding = VectorField(dimensions=EMBEDDING_DIMENSIONS)
    source_text = models.TextField(blank=True)
    indexed_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ("-indexed_at", "-id")
        constraints = [
            models.UniqueConstraint(
                fields=(
                    "product",
                    "language_code",
                    "model_name",
                    "content_hash",
                ),
                condition=Q(variant__isnull=True),
                name="ai_embed_product_unique",
            ),
            models.UniqueConstraint(
                fields=(
                    "product",
                    "variant",
                    "language_code",
                    "model_name",
                    "content_hash",
                ),
                condition=Q(variant__isnull=False),
                name="ai_embed_variant_unique",
            ),
        ]
        indexes = [
            models.Index(
                fields=("product", "model_name", "language_code"),
                name="ai_embed_product_idx",
            ),
            models.Index(
                fields=("content_hash",),
                name="ai_embed_hash_idx",
            ),
            models.Index(
                fields=("-indexed_at",),
                name="ai_embed_indexed_idx",
            ),
            HnswIndex(
                name="ai_embed_vector_hnsw",
                fields=("embedding",),
                m=16,
                ef_construction=64,
                opclasses=("vector_cosine_ops",),
            ),
        ]

    def clean(self) -> None:
        super().clean()
        errors: dict[str, str] = {}
        if self.embedding is not None and len(self.embedding) != EMBEDDING_DIMENSIONS:
            errors["embedding"] = f"Embedding must contain exactly {EMBEDDING_DIMENSIONS} values."
        if self.variant_id and self.product_id and self.variant.product_id != self.product_id:
            errors["variant"] = "Variant must belong to the selected product."
        if errors:
            raise ValidationError(errors)

    def __str__(self) -> str:
        return f"{self.product_id} ({self.model_name}, {self.language_code})"


class AIRequestLog(TimeStampedModel):
    class Feature(models.TextChoices):
        SMART_SEARCH = "smart_search", "Smart search"
        SEMANTIC_SEARCH = "semantic_search", "Semantic search"
        EMBEDDING = "embedding", "Embedding"
        RECOMMENDATION = "recommendation", "Recommendation"
        SIMILAR_PRODUCTS = "similar_products", "Similar products"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"
        FALLBACK = "fallback", "Fallback"
        CACHED = "cached", "Cached"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    request_id = models.CharField(
        max_length=100,
        unique=True,
        default=generate_request_id,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="ai_request_logs",
        null=True,
        blank=True,
    )
    feature = models.CharField(max_length=50, choices=Feature.choices, db_index=True)
    provider = models.CharField(max_length=30, db_index=True)
    model_name = models.CharField(max_length=120)
    prompt_template_version = models.CharField(max_length=50, blank=True)
    prompt = models.TextField(blank=True)
    response = models.TextField(blank=True)
    input_tokens = models.PositiveIntegerField(default=0)
    output_tokens = models.PositiveIntegerField(default=0)
    estimated_cost = models.DecimalField(
        max_digits=18,
        decimal_places=6,
        default=Decimal("0"),
    )
    latency_ms = models.PositiveIntegerField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        db_index=True,
    )
    error_code = models.CharField(max_length=100, blank=True)
    error_message = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ("-created_at", "-id")
        constraints = [
            models.CheckConstraint(
                condition=Q(estimated_cost__gte=0),
                name="ai_log_cost_nonnegative",
            ),
        ]
        indexes = [
            models.Index(
                fields=("feature", "-created_at"),
                name="ai_log_feature_idx",
            ),
            models.Index(
                fields=("provider", "status", "-created_at"),
                name="ai_log_provider_idx",
            ),
            models.Index(
                fields=("user", "-created_at"),
                name="ai_log_user_idx",
            ),
        ]

    def save(self, *args: Any, **kwargs: Any) -> None:
        self.prompt = sanitize_ai_text(
            self.prompt,
            max_length=LOG_PROMPT_MAX_LENGTH,
        )
        self.response = sanitize_ai_text(
            self.response,
            max_length=LOG_RESPONSE_MAX_LENGTH,
        )
        self.error_message = sanitize_ai_text(
            self.error_message,
            max_length=LOG_ERROR_MAX_LENGTH,
        )
        self.metadata = sanitize_ai_payload(self.metadata)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.feature}: {self.status} ({self.request_id})"


class AIContentCache(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    feature = models.CharField(max_length=50, db_index=True)
    entity_type = models.CharField(max_length=50)
    entity_id = models.UUIDField(db_index=True)
    language_code = models.CharField(max_length=10, default="vi")
    content_hash = models.CharField(
        max_length=64,
        validators=[SHA256_VALIDATOR],
    )
    result = models.JSONField(default=dict)
    model_name = models.CharField(max_length=120)
    is_stale = models.BooleanField(default=False, db_index=True)
    generated_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        ordering = ("-generated_at", "-id")
        constraints = [
            models.UniqueConstraint(
                fields=(
                    "feature",
                    "entity_type",
                    "entity_id",
                    "language_code",
                    "content_hash",
                ),
                name="ai_content_cache_unique",
            ),
        ]
        indexes = [
            models.Index(
                fields=("feature", "entity_type", "entity_id"),
                name="ai_cache_entity_idx",
            ),
            models.Index(
                fields=("is_stale", "expires_at"),
                name="ai_cache_freshness_idx",
            ),
        ]

    @property
    def is_expired(self) -> bool:
        return bool(self.expires_at and self.expires_at <= timezone.now())

    def save(self, *args: Any, **kwargs: Any) -> None:
        self.result = sanitize_ai_payload(self.result)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.feature}: {self.entity_type}/{self.entity_id}"
