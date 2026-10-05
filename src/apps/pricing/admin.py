from django.contrib import admin

from .models import (
    CustomerTaxInfo,
    Discount,
    PriceList,
    PriceListEntry,
    ProductTaxSetting,
    ScheduledPrice,
    TaxClass,
    TaxRate,
)


class PriceListEntryInline(admin.TabularInline):
    model = PriceListEntry
    extra = 0


@admin.register(PriceList)
class PriceListAdmin(admin.ModelAdmin):
    list_display = ("name", "store", "role", "customer", "priority", "is_active")
    list_filter = ("is_active",)
    inlines = [PriceListEntryInline]


@admin.register(ScheduledPrice)
class ScheduledPriceAdmin(admin.ModelAdmin):
    list_display = ("product", "variant", "price", "start_at", "end_at", "is_active")


@admin.register(Discount)
class DiscountAdmin(admin.ModelAdmin):
    list_display = (
        "name", "coupon_code", "discount_type", "value", "scope", "used_count", "is_active",
    )
    list_filter = ("discount_type", "scope", "is_active")


@admin.register(TaxClass)
class TaxClassAdmin(admin.ModelAdmin):
    list_display = ("name", "is_default")


@admin.register(TaxRate)
class TaxRateAdmin(admin.ModelAdmin):
    list_display = ("name", "tax_class", "rate", "country", "state", "is_active")
    list_filter = ("tax_class", "is_active")


@admin.register(CustomerTaxInfo)
class CustomerTaxInfoAdmin(admin.ModelAdmin):
    list_display = ("user", "tax_exempt", "tax_id")


@admin.register(ProductTaxSetting)
class ProductTaxSettingAdmin(admin.ModelAdmin):
    list_display = ("product", "tax_class")
