from django.contrib import admin

from .models import (
    Brand,
    Category,
    Product,
    ProductAttribute,
    ProductDownload,
    ProductImage,
    ProductRelation,
    ProductSpecification,
    ProductVariant,
)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "parent", "is_active")
    search_fields = ("name",)


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "store", "product_type", "price", "is_published")
    search_fields = ("name", "slug", "sku")
    list_filter = ("product_type", "is_published", "store")


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ("sku", "product", "price", "stock_quantity", "is_default")


admin.site.register(ProductAttribute)
admin.site.register(ProductImage)
admin.site.register(ProductSpecification)
admin.site.register(ProductRelation)
admin.site.register(ProductDownload)
