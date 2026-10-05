from django.contrib import admin

from .models import InventoryItem, InventoryTransaction, Warehouse, WarehouseLocation


class WarehouseLocationInline(admin.TabularInline):
    model = WarehouseLocation
    extra = 0


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "store", "is_default")
    search_fields = ("name", "code")
    inlines = [WarehouseLocationInline]


@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = ("__str__", "warehouse", "stock_quantity", "reserved_quantity", "stock_status")
    list_filter = ("warehouse",)


@admin.register(InventoryTransaction)
class InventoryTransactionAdmin(admin.ModelAdmin):
    list_display = (
        "inventory_item", "transaction_type", "stock_delta", "reserved_delta",
        "resulting_stock", "resulting_reserved", "actor", "created_at",
    )
    list_filter = ("transaction_type",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
