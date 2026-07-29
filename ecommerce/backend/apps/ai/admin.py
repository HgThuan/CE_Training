from django.contrib import admin

from .models import AIContentCache, AIRequestLog, ProductEmbedding


@admin.register(ProductEmbedding)
class ProductEmbeddingAdmin(admin.ModelAdmin):
    list_display = (
        "product",
        "variant",
        "language_code",
        "model_name",
        "indexed_at",
    )
    list_filter = ("language_code", "model_name")
    search_fields = ("product__name", "content_hash")
    readonly_fields = ("id", "created_at", "updated_at", "indexed_at")


@admin.register(AIRequestLog)
class AIRequestLogAdmin(admin.ModelAdmin):
    list_display = (
        "request_id",
        "feature",
        "provider",
        "model_name",
        "status",
        "latency_ms",
        "created_at",
    )
    list_filter = ("feature", "provider", "status")
    search_fields = ("request_id", "error_code")
    readonly_fields = (
        "id",
        "request_id",
        "user",
        "feature",
        "provider",
        "model_name",
        "prompt_template_version",
        "prompt",
        "response",
        "input_tokens",
        "output_tokens",
        "estimated_cost",
        "latency_ms",
        "status",
        "error_code",
        "error_message",
        "metadata",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False


@admin.register(AIContentCache)
class AIContentCacheAdmin(admin.ModelAdmin):
    list_display = (
        "feature",
        "entity_type",
        "entity_id",
        "model_name",
        "is_stale",
        "generated_at",
        "expires_at",
    )
    list_filter = ("feature", "entity_type", "is_stale", "language_code")
    search_fields = ("entity_id", "content_hash")
    readonly_fields = ("id", "created_at", "updated_at", "generated_at")
