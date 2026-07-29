from django.contrib import admin

from .models import ProductAnswer, ProductQuestion


@admin.register(ProductQuestion)
class ProductQuestionAdmin(admin.ModelAdmin):
    list_display = ("id", "product", "customer", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("content", "product__name", "customer__email")
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(ProductAnswer)
class ProductAnswerAdmin(admin.ModelAdmin):
    list_display = ("id", "question", "seller_user", "created_at")
    search_fields = ("content", "seller_user__email", "question__content")
    readonly_fields = ("id", "created_at", "updated_at")
