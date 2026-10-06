from django.conf import settings
from django.db import models

from core.models import BaseModel


class MediaFile(BaseModel):
    MEDIA_TYPE_IMAGE = "image"
    MEDIA_TYPE_VIDEO = "video"
    MEDIA_TYPE_FILE = "file"
    MEDIA_TYPE_CHOICES = [
        (MEDIA_TYPE_IMAGE, "Image"),
        (MEDIA_TYPE_VIDEO, "Video"),
        (MEDIA_TYPE_FILE, "File"),
    ]

    original_name = models.CharField(max_length=255)
    file = models.FileField(upload_to="media/%Y/%m/")
    thumbnail = models.FileField(upload_to="media/thumbs/%Y/%m/", null=True, blank=True)
    media_type = models.CharField(max_length=10, choices=MEDIA_TYPE_CHOICES, default=MEDIA_TYPE_FILE)
    size = models.PositiveBigIntegerField(default=0)
    content_type = models.CharField(max_length=100, blank=True)
    alt_text = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        related_name="media_files",
        on_delete=models.SET_NULL,
    )

    class Meta:
        verbose_name = "Media file"
        verbose_name_plural = "Media files"
        ordering = ["-created_at"]

    def __str__(self):
        return self.original_name
