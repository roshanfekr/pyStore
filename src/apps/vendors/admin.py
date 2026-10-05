from django.contrib import admin

from .models import Vendor, VendorUser


class VendorUserInline(admin.TabularInline):
    model = VendorUser
    extra = 0


@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "status", "store", "owner")
    search_fields = ("name", "slug", "email")
    list_filter = ("status",)
    inlines = [VendorUserInline]
