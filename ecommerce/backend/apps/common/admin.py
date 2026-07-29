from django.contrib import admin

from .models import AuditLog, SiteSetting


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = (
        "action",
        "actor",
        "target_type",
        "target_id",
        "request_id",
        "created_at",
    )
    list_filter = ("action", "target_type")
    search_fields = ("actor__email", "target_type", "target_id", "request_id")
    readonly_fields = (
        "actor",
        "action",
        "target_type",
        "target_id",
        "reason",
        "request_id",
        "diff",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False


@admin.register(SiteSetting)
class SiteSettingAdmin(admin.ModelAdmin):
    list_display = (
        "key",
        "value_type",
        "is_public",
        "updated_by",
        "updated_at",
    )
    list_filter = ("value_type", "is_public")
    search_fields = ("key", "description")
    readonly_fields = ("id", "updated_by", "created_at", "updated_at")
    fields = (
        "id",
        "key",
        "value",
        "value_type",
        "description",
        "is_public",
        "updated_by",
        "created_at",
        "updated_at",
    )

    def save_model(self, request, obj, form, change) -> None:
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)
