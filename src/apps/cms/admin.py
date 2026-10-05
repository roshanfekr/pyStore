from django.contrib import admin

from .models import BlogCategory, BlogPost, ContentBlock, Menu, MenuItem, Page, Widget


class MenuItemInline(admin.TabularInline):
    model = MenuItem
    extra = 0


@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    list_display = ("title", "slug", "is_published")
    search_fields = ("title", "slug")
    list_filter = ("is_published",)


@admin.register(BlogCategory)
class BlogCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ("title", "slug", "author", "category", "is_published", "published_at")
    list_filter = ("is_published", "category")


@admin.register(Menu)
class MenuAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    inlines = [MenuItemInline]


@admin.register(Widget)
class WidgetAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "widget_type", "is_active")
    list_filter = ("widget_type", "is_active")


@admin.register(ContentBlock)
class ContentBlockAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active")
