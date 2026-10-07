from django.contrib import admin

from .models import MediaFile


@admin.register(MediaFile)
class MediaFileAdmin(admin.ModelAdmin):
    list_display = ("original_name", "media_type", "size", "uploaded_by", "created_at")
    list_filter = ("media_type",)
    search_fields = ("original_name", "alt_text")
