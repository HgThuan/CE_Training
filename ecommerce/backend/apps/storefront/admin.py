from django.contrib import admin

from .models import Banner


@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ("title", "position", "sort_order", "is_active", "starts_at", "ends_at")
    list_filter = ("position", "is_active", "is_deleted")
    search_fields = ("title", "target_url")
    ordering = ("position", "sort_order")
