from django.contrib import admin

from .models import AuditLog


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
