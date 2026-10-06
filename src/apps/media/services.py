import io
import logging
import os

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from PIL import Image, UnidentifiedImageError

from apps.media.models import MediaFile
from core.exceptions import ValidationError

logger = logging.getLogger(__name__)

THUMBNAIL_MAX_SIZE = (300, 300)

DANGEROUS_INTERMEDIATE_EXTENSIONS = {
    "php", "phtml", "phar", "exe", "sh", "bat", "cmd", "ps1",
    "js", "html", "htm", "py", "jar", "dll", "vbs", "asp", "aspx", "jsp",
}


def _allowed_extensions() -> tuple:
    return tuple(settings.MEDIA_ALLOWED_EXTENSIONS)


def validate_upload(file) -> str:
    """Name, extension and size checks applied before anything is stored."""
    original_name = (getattr(file, "name", "") or "").strip()
    if not original_name:
        raise ValidationError("File name is required", code="media.name_required")

    lowered = original_name.lower()
    extension = os.path.splitext(lowered)[1].lstrip(".")
    allowed = _allowed_extensions()
    if extension and extension not in allowed:
        raise ValidationError(
            f"File extension .{extension} is not allowed", code="media.extension_not_allowed"
        )

    parts = lowered.split(".")
    dangerous = DANGEROUS_INTERMEDIATE_EXTENSIONS & set(parts[1:-1])
    if dangerous:
        raise ValidationError(
            "File name contains a forbidden extension", code="media.extension_not_allowed"
        )

    max_size = getattr(settings, "MEDIA_MAX_UPLOAD_SIZE", 10 * 1024 * 1024)
    if getattr(file, "size", 0) > max_size:
        raise ValidationError(
            f"File exceeds the maximum size of {max_size // (1024 * 1024)} MB",
            code="media.file_too_large",
        )
    return original_name


def detect_media_type(name: str, content_type: str = "") -> str:
    lowered = (content_type or "").lower()
    if lowered.startswith("image/") or name.lower().endswith(
        (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp")
    ):
        return MediaFile.MEDIA_TYPE_IMAGE
    if lowered.startswith("video/") or name.lower().endswith(
        (".mp4", ".webm", ".mov", ".avi", ".mkv")
    ):
        return MediaFile.MEDIA_TYPE_VIDEO
    return MediaFile.MEDIA_TYPE_FILE


def _store_thumbnail(image: Image.Image) -> str:
    working = image
    if working.mode not in ("RGB", "L"):
        working = working.convert("RGB")
    working.thumbnail(THUMBNAIL_MAX_SIZE)
    buffer = io.BytesIO()
    working.save(buffer, format="PNG")
    name = default_storage.save("media/thumbs/thumb.png", ContentFile(buffer.getvalue()))
    return name


def upload_media(file, *, alt_text: str = "", uploaded_by=None) -> MediaFile:
    original_name = validate_upload(file)
    content_type = getattr(file, "content_type", "") or ""
    media_type = detect_media_type(original_name, content_type)
    data = file.read()
    if not data:
        raise ValidationError("File is empty", code="media.empty_file")

    stored_name = default_storage.save(f"media/{original_name}", ContentFile(data))
    stored = default_storage.open(stored_name, "rb")

    metadata: dict = {}
    thumbnail_name = None
    if media_type == MediaFile.MEDIA_TYPE_IMAGE:
        try:
            image = Image.open(stored)
            image.load()
            metadata = {"width": image.width, "height": image.height}
            thumbnail_name = _store_thumbnail(image)
        except UnidentifiedImageError:
            logger.warning("Uploaded file %s is not a readable image", original_name)
            media_type = MediaFile.MEDIA_TYPE_FILE
        finally:
            stored.seek(0)

    media = MediaFile.objects.create(
        original_name=original_name,
        file=stored_name,
        thumbnail=thumbnail_name,
        media_type=media_type,
        size=len(data),
        content_type=content_type,
        alt_text=alt_text,
        metadata=metadata,
        uploaded_by=uploaded_by,
    )
    logger.info("Media uploaded: %s (%s, %s bytes)", media.pk, media.media_type, media.size)
    return media


def delete_media(media: MediaFile) -> None:
    for field_name in ("file", "thumbnail"):
        stored = getattr(media, field_name)
        if stored and stored.name and default_storage.exists(stored.name):
            default_storage.delete(stored.name)
    media.delete()
    logger.info("Media deleted: %s", media.pk)
