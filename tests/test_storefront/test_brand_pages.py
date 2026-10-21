from decimal import Decimal

import pytest
from django.test import Client, override_settings

from apps.catalog.models import Brand
from apps.catalog.services import create_product, publish_product
from apps.stores.services import create_store

pytestmark = [pytest.mark.django_db]


@pytest.fixture
def store(db):
    return create_store("Brand Page Store")


@pytest.fixture
def active_brand(db):
    return Brand.objects.create(
        name="Acme", slug="acme", description="Acme makes everything.", is_active=True
    )


@pytest.fixture
def inactive_brand(db):
    return Brand.objects.create(
        name="Old Co", slug="old-co", description="Retired brand.", is_active=False
    )


def test_brand_list_page_shows_active_brands_only(client, active_brand, inactive_brand):
    response = client.get("/brands/")
    assert response.status_code == 200
    content = response.content.decode()
    assert "Acme" in content
    assert "Old Co" not in content


def test_brand_list_page_shows_empty_state(client, db):
    response = client.get("/brands/")
    assert response.status_code == 200
    assert "No brands available." in response.content.decode()


def test_brand_detail_page_shows_brand_and_its_published_products(
    client, store, active_brand
):
    published = create_product(
        store, "Acme Product", price=Decimal("10.0000"), brand=active_brand
    )
    publish_product(published)
    hidden = create_product(
        store, "Acme Hidden", price=Decimal("12.0000"), brand=active_brand
    )
    assert hidden.is_published is False

    response = client.get("/brands/acme/")
    assert response.status_code == 200
    content = response.content.decode()
    assert "Acme" in content
    assert "Acme makes everything." in content
    assert "Acme Product" in content
    assert "Acme Hidden" not in content


def test_brand_detail_page_without_logo_falls_back_to_the_initial(
    client, store, active_brand
):
    response = client.get("/brands/acme/")
    assert response.status_code == 200
    content = response.content.decode()
    assert "brand-logo-fallback" in content
    assert ">A<" in content


def test_inactive_brand_detail_page_is_not_found(client, inactive_brand):
    assert client.get("/brands/old-co/").status_code == 404


def test_unknown_brand_detail_page_is_not_found(client, db):
    assert client.get("/brands/missing/").status_code == 404


def test_brand_routes_are_served_by_the_spa_when_it_is_enabled(tmp_path):
    (tmp_path / "index.html").write_text("<div id='app'>SPA SHELL</div>", encoding="utf-8")
    with override_settings(STOREFRONT_SPA_ENABLED=True, STOREFRONT_SPA_DIR=str(tmp_path)):
        listing = Client().get("/brands/")
        detail = Client().get("/brands/acme/")
    assert listing.status_code == 200
    assert "SPA SHELL" in listing.content.decode()
    assert detail.status_code == 200
    assert "SPA SHELL" in detail.content.decode()
