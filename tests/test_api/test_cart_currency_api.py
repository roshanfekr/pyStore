from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.catalog.services import create_product, publish_product
from apps.pricing.models import ProductPrice
from apps.stores.services import create_store, upsert_currency

pytestmark = [pytest.mark.django_db]


@pytest.fixture
def store(db):
    return create_store("Currency API Store")


@pytest.fixture
def usd(db):
    """USD as a configured, active currency (FR-CUR-001)."""
    return upsert_currency("US Dollar", "USD", symbol="$", decimal_places=2)


@pytest.fixture
def eur(db):
    return upsert_currency("Euro", "EUR", symbol="€", decimal_places=2)


@pytest.fixture
def product(db, store):
    product = create_product(
        store, "Currency API Product", price=Decimal("100.0000"), stock_quantity=10
    )
    publish_product(product)
    return product


@pytest.fixture
def usd_client(store, db):
    client = APIClient(headers={"X-Cart-Session": "currency-session-1", "X-Store": store.slug})
    client.cookies["pystore_currency"] = "USD"
    return client


def test_cart_reports_the_active_currency(usd_client, store, product, usd):
    response = usd_client.get("/api/v1/cart")
    assert response.status_code == 200
    assert response.data["currency"] == "USD"


def test_cart_uses_the_explicit_currency_price(usd_client, store, product, usd):
    ProductPrice.objects.create(product=product, currency="USD", price=Decimal("18.0000"))

    response = usd_client.post("/api/v1/cart/items", {"product": product.slug}, format="json")

    assert response.status_code == 201, response.data
    assert response.data["currency"] == "USD"
    assert response.data["lines"][0]["unit_price"] == "18.0000"
    assert response.data["subtotal"] == "18.0000"


def test_product_without_explicit_price_cannot_be_added(usd_client, store, product, usd):
    response = usd_client.post("/api/v1/cart/items", {"product": product.slug}, format="json")

    assert response.status_code == 400
    assert response.data["error"]["code"] == "cart.price_unavailable"


def test_cart_keeps_its_currency_when_the_customer_switches(usd_client, store, product, usd):
    ProductPrice.objects.create(product=product, currency="USD", price=Decimal("18.0000"))
    add = usd_client.post("/api/v1/cart/items", {"product": product.slug}, format="json")
    assert add.status_code == 201

    switched = APIClient(headers={"X-Cart-Session": "currency-session-1", "X-Store": store.slug})
    switched.cookies["pystore_currency"] = "EUR"
    ProductPrice.objects.create(product=product, currency="EUR", price=Decimal("17.0000"))

    response = switched.post("/api/v1/cart/items", {"product": product.slug}, format="json")

    assert response.status_code == 400
    assert response.data["error"]["code"] == "cart.currency_mismatch"
    # The stored lines keep their original currency prices.
    detail = usd_client.get("/api/v1/cart")
    assert detail.data["currency"] == "USD"
    assert detail.data["subtotal"] == "18.0000"


def test_empty_cart_adopts_the_new_currency_on_add(usd_client, store, product, usd, eur):
    # An empty USD cart exists after browsing.
    usd_client.get("/api/v1/cart")

    switched = APIClient(headers={"X-Cart-Session": "currency-session-1", "X-Store": store.slug})
    switched.cookies["pystore_currency"] = "EUR"
    ProductPrice.objects.create(product=product, currency="EUR", price=Decimal("17.0000"))

    response = switched.post("/api/v1/cart/items", {"product": product.slug}, format="json")

    assert response.status_code == 201
    assert response.data["currency"] == "EUR"
    assert response.data["lines"][0]["unit_price"] == "17.0000"