from django.contrib import admin

from .models import PaymentMethod, ShippingMethod


@admin.register(ShippingMethod)
class ShippingMethodAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "store", "flat_price", "is_active")
    list_filter = ("store", "is_active")


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "is_active")
    list_filter = ("is_active",)
