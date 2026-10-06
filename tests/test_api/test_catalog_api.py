from decimal import Decimal

import pytest

from apps.catalog.services import create_product, publish_product
from apps.stores.services import create_store

pytestmark = [pytest.mark.django_db]


@pytest.fixture
def store(db):
    return create_store("API Store")


@pytest.fixture
def products(db, store):
    published = create_product(store, "Alpha Product", price=Decimal("10.0000"))
    publish_product(published)
    second = create_product(store, "Beta Product", price=Decimal("20.0000"))
    publish_product(second)
    hidden = create_product(store, "Hidden Product", price=Decimal("30.0000"))
    return published, second, hidden


def test_products_list_public_returns_published_only(api_client, products):
    response = api_client.get("/api/v1/products")
    assert response.status_code == 200
    assert response.data["count"] == 2
    names = {item["name"] for item in response.data["results"]}
    assert "Hidden Product" not in names


def test_products_search_and_price_filter(api_client, products):
    response = api_client.get("/api/v1/products", {"search": "alpha"})
    assert response.data["count"] == 1
    assert response.data["results"][0]["name"] == "Alpha Product"

    response = api_client.get("/api/v1/products", {"price_min": "15"})
    names = {item["name"] for item in response.data["results"]}
    assert names == {"Beta Product"}


def test_products_ordering_and_pagination(api_client, products):
    response = api_client.get("/api/v1/products", {"ordering": "price", "page_size": "1"})
    assert response.data["results"][0]["name"] == "Alpha Product"
    assert response.data["next"] is not None

    response = api_client.get("/api/v1/products", {"ordering": "-price"})
    assert response.data["results"][0]["name"] == "Beta Product"

    response = api_client.get("/api/v1/products", {"ordering": "hacker"})
    assert response.data["results"][0]["name"] == "Beta Product"


def test_product_detail_by_slug(api_client, products):
    published = products[0]
    response = api_client.get(f"/api/v1/products/{published.slug}")
    assert response.status_code == 200
    assert response.data["price"] == "10.0000"


def test_product_create_requires_permission(api_client, user, store):
    response = api_client.post(
        "/api/v1/products", {"name": "NoPerm", "price": "5"}, format="json"
    )
    assert response.status_code == 401

    from rest_framework.test import APIClient

    client = APIClient()
    client.force_authenticate(user=user)
    response = client.post("/api/v1/products", {"name": "NoPerm", "price": "5"}, format="json")
    assert response.status_code == 403


def test_product_create_with_permission(api_client, user, store):
    from .conftest import grant_permission

    grant_permission(user, "catalog.product.create")
    client = api_client
    client.force_authenticate(user=user)
    response = client.post(
        "/api/v1/products",
        {"name": "API Created", "price": "12.5", "store": store.slug},
        format="json",
    )
    assert response.status_code == 201
    assert response.data["slug"] == "api-created"
    assert response.data["store"] == store.id


def test_product_update_and_publish_flow(api_client, user, store, products):
    from .conftest import grant_permission

    grant_permission(user, "catalog.product.update")
    client = api_client
    client.force_authenticate(user=user)
    product = products[2]

    response = client.patch(
        f"/api/v1/products/{product.slug}", {"price": "33.0000"}, format="json"
    )
    assert response.status_code == 200
    assert response.data["price"] == "33.0000"

    response = client.post(f"/api/v1/products/{product.slug}/publish")
    assert response.status_code == 200
    assert response.data["is_published"] is True


def test_product_delete_requires_delete_permission(api_client, user, store, products):
    from .conftest import grant_permission

    grant_permission(user, "catalog.product.update")
    client = api_client
    client.force_authenticate(user=user)
    product = products[2]
    assert client.delete(f"/api/v1/products/{product.slug}").status_code == 403

    grant_permission(user, "catalog.product.delete")
    assert client.delete(f"/api/v1/products/{product.slug}").status_code == 204


def test_categories_crud_and_permissions(api_client, user, db):
    response = api_client.get("/api/v1/categories")
    assert response.status_code == 200

    response = api_client.post("/api/v1/categories", {"name": "Books"}, format="json")
    assert response.status_code in (401, 403)

    from .conftest import grant_permission

    grant_permission(user, "catalog.category.manage")
    client = api_client
    client.force_authenticate(user=user)
    response = client.post("/api/v1/categories", {"name": "Books"}, format="json")
    assert response.status_code == 201
    slug = response.data["slug"]

    child = client.post(
        "/api/v1/categories", {"name": "Fiction", "parent": slug}, format="json"
    )
    assert child.status_code == 201
    assert child.data["parent"] == slug


def test_brands_list_and_filter(api_client, user, db):
    from apps.catalog.models import Brand

    Brand.objects.create(name="Acme", slug="acme", is_active=True)
    Brand.objects.create(name="Old Co", slug="old-co", is_active=False)

    response = api_client.get("/api/v1/brands", {"is_active": "true"})
    assert {item["slug"] for item in response.data["results"]} == {"acme"}
