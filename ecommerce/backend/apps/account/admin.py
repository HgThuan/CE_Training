from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import Address, AdminProfile, CustomerProfile, SellerProfile, User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    ordering = ("email",)
    list_display = (
        "email",
        "full_name",
        "role",
        "is_email_verified",
        "is_active",
        "is_deleted",
    )
    list_filter = ("role", "is_email_verified", "is_active", "is_deleted", "is_staff")
    search_fields = ("email", "full_name", "phone")
    readonly_fields = ("last_login", "created_at", "updated_at", "token_version")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (
            "Thông tin cá nhân",
            {"fields": ("full_name", "phone", "date_of_birth", "gender", "avatar_url")},
        ),
        (
            "Phân quyền và trạng thái",
            {
                "fields": (
                    "role",
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "is_email_verified",
                    "must_change_password",
                    "is_deleted",
                    "deleted_at",
                    "lock_reason",
                    "locked_at",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Phiên đăng nhập", {"fields": ("token_version", "last_login")}),
        ("Thời gian", {"fields": ("created_at", "updated_at")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "password1",
                    "password2",
                    "role",
                    "is_email_verified",
                    "is_staff",
                ),
            },
        ),
    )


admin.site.register(CustomerProfile)
admin.site.register(Address)
admin.site.register(SellerProfile)
admin.site.register(AdminProfile)
