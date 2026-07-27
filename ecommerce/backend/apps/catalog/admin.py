from django.contrib import admin

from .models import Brand, Category


class ReadOnlyCatalogAdminMixin:
    def has_add_permission(self, request) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False


@admin.register(Category)
class CategoryAdmin(ReadOnlyCatalogAdminMixin, admin.ModelAdmin):
    list_display = (
        "name",
        "parent",
        "slug",
        "sort_order",
        "is_active",
        "is_deleted",
        "updated_at",
    )
    list_filter = ("is_active", "is_deleted")
    search_fields = ("name", "slug")
    ordering = ("sort_order", "name")
    readonly_fields = (
        "id",
        "parent",
        "name",
        "slug",
        "image_url",
        "sort_order",
        "is_active",
        "is_deleted",
        "deleted_at",
        "created_at",
        "updated_at",
    )


@admin.register(Brand)
class BrandAdmin(ReadOnlyCatalogAdminMixin, admin.ModelAdmin):
    list_display = ("name", "slug", "is_active", "is_deleted", "updated_at")
    list_filter = ("is_active", "is_deleted")
    search_fields = ("name", "slug")
    ordering = ("name",)
    readonly_fields = (
        "id",
        "name",
        "slug",
        "logo_url",
        "description",
        "is_active",
        "is_deleted",
        "deleted_at",
        "created_at",
        "updated_at",
    )
