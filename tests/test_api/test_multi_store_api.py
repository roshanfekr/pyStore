"""Multi-store scoping of the SPA/API requests (X-Store header contract)."""

from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.catalog.services import create_product, publish_product
from apps.stores.services import create_store

pytestmark = [pytest.mark.django_db]


@pytest.fixture
def store_a(db):
    return create_store("Store A")


@pytest.fixture
def store_b(db):
    return create_store("Store B")


@pytest.fixture
def product_a(store_a):
    product = create_product(store_a, "Product A", price=Decimal("10.0000"), stock_quantity=5)
    publish_product(product)
    return product


@pytest.fixture
def product_b(store_b):
    product = create_product(store_b, "Product B", price=Decimal("20.0000"), stock_quantity=5)
    publish_product(product)
    return product


def test_store_header_scopes_the_cart_to_that_store(store_a, store_b, product_a, product_b):
    client_a = APIClient(headers={"X-Cart-Session": "shared-session", "X-Store": store_a.slug})
    client_b = APIClient(headers={"X-Cart-Session": "shared-session", "X-Store": store_b.slug})

    response = client_a.post("/api/v1/cart/items", {"product": product_a.slug}, format="json")
    assert response.status_code == 201, response.data

    # The same session key in another store is a different cart, and the other
    # store's cart never sees store A's lines.
    other = client_b.get("/api/v1/cart")
    assert other.status_code == 200
    assert other.data["lines"] == []

    # A product of another store cannot be added to this store's cart.
    response = client_b.post("/api/v1/cart/items", {"product": product_a.slug}, format="json")
    assert response.status_code == 400
    assert response.data["error"]["code"] == "cart.store_mismatch"


def test_cart_without_store_header_targets_the_default_store(store_a, store_b, product_a):
    from apps.stores.services import set_primary_store

    set_primary_store(store_a)

    client = APIClient(headers={"X-Cart-Session": "default-store-session"})
    response = client.post("/api/v1/cart/items", {"product": product_a.slug}, format="json")

    assert response.status_code == 201, response.data


def test_checkout_methods_honor_the_store_header(store_a, store_b, product_a):
    from apps.checkout.models import ShippingMethod

    ShippingMethod.objects.create(store=store_b, code="EXPRESS", name="Express B")

    scoped = APIClient(headers={"X-Store": store_a.slug})
    response = scoped.get("/api/v1/checkout/methods")
    assert response.status_code == 200
    # Store B's shipping method is not offered for store A.
    assert response.data["shipping_methods"] == []

    other = APIClient(headers={"X-Store": store_b.slug})
    response = other.get("/api/v1/checkout/methods")
    assert [method["code"] for method in response.data["shipping_methods"]] == ["EXPRESS"]


def test_bootstrap_exposes_the_current_store(store_a, store_b):
    from apps.stores.services import set_primary_store

    set_primary_store(store_a)

    response = APIClient().get("/api/v1/storefront/bootstrap")
    assert response.status_code == 200
    assert response.data["store"]["slug"] == store_a.slug
    assert response.data["store"]["name"] == store_a.name
