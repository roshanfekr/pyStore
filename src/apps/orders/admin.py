from django.contrib import admin

from .models import Order, OrderAddress, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


class OrderAddressInline(admin.TabularInline):
    model = OrderAddress
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "number", "store", "user", "email", "status", "payment_status", "total", "created_at",
    )
    list_filter = ("status", "payment_status", "shipment_status", "store")
    search_fields = ("number", "email")
    inlines = [OrderItemInline, OrderAddressInline]
