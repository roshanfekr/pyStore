from django.contrib import admin

from .models import Store, StoreDomain


class StoreDomainInline(admin.TabularInline):
    model = StoreDomain
    extra = 0


@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_default", "is_active", "default_language", "default_currency")
    search_fields = ("name", "slug")
    list_filter = ("is_active", "is_default")
    inlines = [StoreDomainInline]
