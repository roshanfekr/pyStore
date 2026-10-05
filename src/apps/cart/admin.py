from django.contrib import admin

from .models import Cart, CartItem, CompareItem, WishlistItem


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ("__str__", "store", "status", "coupon")
    list_filter = ("status", "store")
    inlines = [CartItemInline]


@admin.register(WishlistItem)
class WishlistItemAdmin(admin.ModelAdmin):
    list_display = ("user", "product", "created_at")


@admin.register(CompareItem)
class CompareItemAdmin(admin.ModelAdmin):
    list_display = ("user", "session_key", "product")
