import io

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.catalog.models import ProductImage
from apps.catalog.services import create_product

User = get_user_model()

pytestmark = [pytest.mark.django_db]


def _png_file(name="product.png"):
    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (40, 40), color=(10, 120, 220)).save(buffer, format="PNG")
    buffer.seek(0)
    return SimpleUploadedFile(name, buffer.read(), content_type="image/png")


@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser(email="images@example.com", password="Str0ng!Passw0rd")


@pytest.fixture
def store(db):
    from apps.stores.services import create_store

    return create_store("Images Store")


@pytest.fixture
def product(store):
    return create_product(store, "Imaged Product", price="10.00")


def test_change_form_renders_images_dialog(client, admin_user, product):
    client.force_login(admin_user)
    response = client.get(f"/admin/catalog/product/{product.pk}/change/")
    content = response.content.decode()
    assert response.status_code == 200
    assert 'id="ps-product-images"' in content
    assert 'id="ps-images-modal"' in content
    assert "admin_panel/js/product_images.js" in content


def test_admin_pages_load_bootstrap5(client, admin_user):
    client.force_login(admin_user)
    content = client.get("/admin/").content.decode()
    assert "admin_panel/vendor/bootstrap/bootstrap.min.css" in content
    assert "admin_panel/vendor/bootstrap/bootstrap.bundle.min.js" in content


def test_image_upload_endpoint_creates_image(client, admin_user, product):
    client.force_login(admin_user)
    response = client.post(
        f"/admin/catalog/product/{product.pk}/images/upload/",
        {"image": _png_file(), "alt_text": "Front view"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["image"]["alt_text"] == "Front view"
    assert payload["image"]["is_main"] is True

    image = ProductImage.objects.get(product=product)
    assert image.alt_text == "Front view"
    assert image.is_main is True


def test_image_delete_and_main_endpoints(client, admin_user, product):
    first = ProductImage.objects.create(product=product, image=_png_file("a.png"), is_main=True)
    second = ProductImage.objects.create(product=product, image=_png_file("b.png"))

    client.force_login(admin_user)

    main_response = client.post(
        f"/admin/catalog/product/{product.pk}/images/{second.pk}/main/"
    )
    assert main_response.status_code == 200
    second.refresh_from_db()
    first.refresh_from_db()
    assert second.is_main is True
    assert first.is_main is False

    delete_response = client.post(
        f"/admin/catalog/product/{product.pk}/images/{first.pk}/delete/"
    )
    assert delete_response.status_code == 200
    assert not ProductImage.objects.filter(pk=first.pk).exists()


def test_image_upload_rejects_bad_extension(client, admin_user, product):
    client.force_login(admin_user)
    bad = SimpleUploadedFile("evil.exe", b"MZ", content_type="application/octet-stream")
    response = client.post(
        f"/admin/catalog/product/{product.pk}/images/upload/",
        {"image": bad},
    )
    assert response.status_code == 400
    assert response.json()["ok"] is False
    assert not ProductImage.objects.filter(product=product).exists()


def test_image_upload_requires_permission(client, product, db):
    staff = User.objects.create_user(
        email="plain@example.com", password="Str0ng!Passw0rd", is_staff=True
    )
    client.force_login(staff)
    response = client.post(
        f"/admin/catalog/product/{product.pk}/images/upload/",
        {"image": _png_file()},
    )
    assert response.status_code == 403
    assert not ProductImage.objects.filter(product=product).exists()
