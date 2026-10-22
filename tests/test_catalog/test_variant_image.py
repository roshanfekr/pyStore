from decimal import Decimal

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings

from apps.catalog.models import ProductVariant
from apps.catalog.services import add_variant, create_product
from apps.stores.services import create_store

pytestmark = [pytest.mark.django_db]

PNG_BYTES = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000d49444154789c6260000000060005"
    "27de58ce0000000049454e44ae426082"
)


@pytest.fixture
def store(db):
    return create_store("Variant Image Store")


@pytest.fixture
def variant(store):
    product = create_product(store, "Image Product", product_type="variant")
    return add_variant(product, "IMG-1", Decimal("50.0000"))


def test_variant_image_is_optional(variant):
    variant.full_clean()
    assert not variant.image


def test_variant_image_accepts_a_valid_png(variant):
    variant.image = SimpleUploadedFile("red.png", PNG_BYTES, content_type="image/png")
    variant.full_clean()
    variant.save()
    variant.refresh_from_db()
    assert variant.image.name.startswith("catalog/variants/")


def test_variant_image_rejects_a_disallowed_extension(variant):
    variant.image = SimpleUploadedFile("script.php", b"not-an-image", content_type="application/x-php")
    with pytest.raises(Exception) as error:
        variant.full_clean()
    assert "extension" in str(error.value).lower()


def test_variant_image_rejects_an_oversized_file(variant):
    with override_settings(MEDIA_MAX_UPLOAD_SIZE=10):
        variant.image = SimpleUploadedFile("big.png", PNG_BYTES * 10, content_type="image/png")
        with pytest.raises(Exception) as error:
            variant.full_clean()
    assert "maximum size" in str(error.value)


def test_variant_image_rejects_a_non_image_content(variant):
    # The image content itself is validated by Django's ImageField form field
    # (Pillow), as on the admin's product/variant forms.
    from django import forms as django_forms

    class _VariantImageForm(django_forms.ModelForm):
        class Meta:
            model = ProductVariant
            fields = ["image"]

    form = _VariantImageForm(
        {},
        {"image": SimpleUploadedFile("payload.png", b"definitely not an image", content_type="image/png")},
    )
    assert not form.is_valid()
    assert any("valid image" in message for message in form.errors["image"])


def test_existing_variant_image_stays_valid_on_resave(variant):
    variant.image = SimpleUploadedFile("red.png", PNG_BYTES, content_type="image/png")
    variant.save()
    loaded = ProductVariant.objects.get(pk=variant.pk)
    loaded.full_clean()
