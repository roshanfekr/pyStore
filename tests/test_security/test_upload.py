import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from apps.media.services import delete_media, upload_media
from core.exceptions import ValidationError


def png_file(name="banner.png"):
    buffer = io.BytesIO()
    Image.new("RGB", (10, 10), color=(10, 10, 10)).save(buffer, format="PNG")
    buffer.seek(0)
    return SimpleUploadedFile(name, buffer.read(), content_type="image/png")


def test_upload_rejects_disallowed_extension(db):
    with pytest.raises(ValidationError, match="extension"):
        upload_media(SimpleUploadedFile("malware.exe", b"MZ..."))


def test_upload_rejects_oversized_file(db, settings):
    settings.MEDIA_MAX_UPLOAD_SIZE = 100
    big = SimpleUploadedFile("big.png", b"x" * 101, content_type="image/png")
    with pytest.raises(ValidationError, match="maximum size"):
        upload_media(big)


def test_upload_rejects_double_extension_trick(db):
    with pytest.raises(ValidationError, match="extension"):
        upload_media(SimpleUploadedFile("shell.php.png", b"data"))


def test_upload_allowed_extension_still_works(db):
    media = upload_media(png_file())
    try:
        assert media.media_type == "image"
    finally:
        delete_media(media)
