from django.contrib import admin

from .models import (
    ProductAnswer,
    ProductQuestion,
    ShopFollower,
    Wishlist,
    WishlistItem,
)


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


@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "created_at")
    search_fields = ("user__email",)
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(WishlistItem)
class WishlistItemAdmin(admin.ModelAdmin):
    list_display = ("id", "wishlist", "product", "price_when_added", "created_at")
    search_fields = ("wishlist__user__email", "product__name")
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(ShopFollower)
class ShopFollowerAdmin(admin.ModelAdmin):
    list_display = ("id", "shop", "user", "created_at")
    search_fields = ("shop__name", "user__email")
    readonly_fields = ("id", "created_at", "updated_at")
