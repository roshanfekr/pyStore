import io
from decimal import Decimal

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from rest_framework.test import APIClient

from apps.catalog.models import Brand
from apps.catalog.services import create_product, publish_product
from apps.stores.services import create_store

pytestmark = [pytest.mark.django_db]


def png_file(name="acme.png"):
    buffer = io.BytesIO()
    Image.new("RGB", (10, 10), color=(10, 10, 10)).save(buffer, format="PNG")
    buffer.seek(0)
    return SimpleUploadedFile(name, buffer.read(), content_type="image/png")


@pytest.fixture
def store(db):
    return create_store("Brand API Store")


@pytest.fixture
def active_brand(db):
    return Brand.objects.create(
        name="Acme",
        slug="acme",
        description="Acme makes everything.",
        is_active=True,
    )


@pytest.fixture
def inactive_brand(db):
    return Brand.objects.create(
        name="Old Co",
        slug="old-co",
        description="Old Co is retired.",
        is_active=False,
    )


def test_brand_serializer_exposes_logo_and_seo_metadata(api_client, active_brand, tmp_path, settings):
    settings.MEDIA_ROOT = str(tmp_path)
    active_brand.logo.save("acme.png", png_file(), save=True)

    response = api_client.get("/api/v1/brands/acme")
    assert response.status_code == 200
    assert response.data["name"] == "Acme"
    assert response.data["description"] == "Acme makes everything."
    assert response.data["logo"].endswith("acme.png")
    assert response.data["meta_title"] == ""
    assert response.data["robots_meta"] == "index, follow"


def test_brand_seo_metadata_is_stored_and_returned(api_client, active_brand):
    active_brand.meta_title = "Acme | Official Store"
    active_brand.meta_description = "Buy Acme products."
    active_brand.canonical_url = "https://example.test/brands/acme"
    active_brand.og_title = "Acme on social"
    active_brand.structured_data = {"@type": "Organization"}
    active_brand.save()

    response = api_client.get("/api/v1/brands/acme")
    assert response.status_code == 200
    assert response.data["meta_title"] == "Acme | Official Store"
    assert response.data["meta_description"] == "Buy Acme products."
    assert response.data["canonical_url"] == "https://example.test/brands/acme"
    assert response.data["og_title"] == "Acme on social"
    assert response.data["structured_data"] == {"@type": "Organization"}


def test_brand_seo_metadata_falls_back_to_name_and_description(api_client, active_brand):
    # FR-CAT-007: SEO metadata is optional and falls back to the brand name
    # and description when it is not configured.
    assert active_brand.effective_meta_title == "Acme"
    assert active_brand.effective_meta_description == "Acme makes everything."

    response = api_client.get("/api/v1/brands/acme")
    assert response.status_code == 200
    assert response.data["effective_meta_title"] == "Acme"
    assert response.data["effective_meta_description"] == "Acme makes everything."


def test_brand_without_logo_has_no_logo(active_brand):
    # The logo is optional; the storefront renders its fallback presentation
    # for a brand that has no logo.
    assert not active_brand.logo
    assert Brand._meta.get_field("logo").blank is True


def test_public_brand_list_exposes_active_brands_only(api_client, active_brand, inactive_brand):
    response = api_client.get("/api/v1/brands")
    assert response.status_code == 200
    slugs = {item["slug"] for item in response.data["results"]}
    assert slugs == {"acme"}


def test_public_brand_list_cannot_request_inactive_brands(api_client, active_brand, inactive_brand):
    response = api_client.get("/api/v1/brands", {"is_active": "false"})
    assert response.status_code == 200
    assert response.data["count"] == 0
    assert response.data["results"] == []


def test_inactive_brand_cannot_be_retrieved_by_slug(api_client, inactive_brand):
    response = api_client.get("/api/v1/brands/old-co")
    assert response.status_code == 404


def test_inactive_brand_cannot_be_retrieved_by_id(api_client, inactive_brand):
    response = api_client.get(f"/api/v1/brands/{inactive_brand.pk}")
    assert response.status_code == 404


def test_unknown_brand_returns_not_found(api_client, db):
    assert api_client.get("/api/v1/brands/does-not-exist").status_code == 404


def test_staff_with_brand_permission_still_sees_inactive_brands(api_client, user, inactive_brand):
    from .conftest import grant_permission

    grant_permission(user, "catalog.brand.manage")
    client = APIClient()
    client.force_authenticate(user=user)

    listing = client.get("/api/v1/brands")
    assert listing.status_code == 200
    slugs = {item["slug"] for item in listing.data["results"]}
    assert slugs == {"old-co"}

    detail = client.get("/api/v1/brands/old-co")
    assert detail.status_code == 200
    assert detail.data["name"] == "Old Co"


def test_products_can_be_filtered_by_active_brand_slug(api_client, store, active_brand):
    product = create_product(
        store, "Acme Product", price=Decimal("10.0000"), brand=active_brand
    )
    publish_product(product)

    response = api_client.get("/api/v1/products", {"brand": "acme"})
    assert response.status_code == 200
    assert response.data["count"] == 1
    assert response.data["results"][0]["name"] == "Acme Product"


def test_product_filtering_by_brand_slug_is_preserved_for_inactive_brands(
    api_client, store, inactive_brand
):
    # FR-CAT-006 scopes the exposure rule to the public brand surfaces, so
    # product filtering by brand slug keeps its existing behavior. This is
    # recorded here so the decision is explicit and regression-guarded.
    product = create_product(
        store, "Old Co Product", price=Decimal("10.0000"), brand=inactive_brand
    )
    publish_product(product)

    response = api_client.get("/api/v1/products", {"brand": "old-co"})
    assert response.status_code == 200
    assert response.data["count"] == 1
    assert response.data["results"][0]["name"] == "Old Co Product"
