from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.cart.services import get_or_create_cart
from apps.catalog.services import create_product, publish_product
from apps.checkout.models import ensure_default_payment_methods
from apps.stores.services import create_store

pytestmark = [pytest.mark.django_db]

ADDRESS = {
    "country": "IR",
    "city": "Tehran",
    "address_line": "Test 1",
    "phone": "+989121234567",
}


@pytest.fixture
def store(db):
    return create_store("Cart API Store")


@pytest.fixture
def product(db, store):
    product = create_product(store, "Cart API Product", price=Decimal("10.0000"), stock_quantity=10)
    publish_product(product)
    return product


@pytest.fixture
def cart_client(api_client, store):
    client = APIClient(headers={"X-Cart-Session": "guest-session-1", "X-Store": store.slug})
    return client


def test_guest_cart_add_and_view(cart_client, product):
    response = cart_client.post(
        "/api/v1/cart/items",
        {"product": product.slug, "quantity": 2},
        format="json",
    )
    assert response.status_code == 201, response.data
    assert response.data["subtotal"] == "20.0000"
    assert response.data["lines"][0]["product_name"] == "Cart API Product"

    response = cart_client.get("/api/v1/cart")
    assert response.data["subtotal"] == "20.0000"


def test_cart_update_and_remove_item(cart_client, product):
    add = cart_client.post("/api/v1/cart/items", {"product": product.slug}, format="json")
    item_id = add.data["lines"][0]["item_id"]

    response = cart_client.patch(
        f"/api/v1/cart/items/{item_id}", {"quantity": 5}, format="json"
    )
    assert response.data["lines"][0]["quantity"] == 5

    response = cart_client.delete(f"/api/v1/cart/items/{item_id}")
    assert response.status_code == 204
    response = cart_client.get("/api/v1/cart")
    assert response.data["lines"] == []


def test_cart_zero_quantity_removes_item(cart_client, product):
    add = cart_client.post("/api/v1/cart/items", {"product": product.slug}, format="json")
    item_id = add.data["lines"][0]["item_id"]
    cart_client.patch(f"/api/v1/cart/items/{item_id}", {"quantity": 0}, format="json")
    response = cart_client.get("/api/v1/cart")
    assert response.data["lines"] == []


def test_cart_item_requires_existing_product(cart_client, db):
    response = cart_client.post(
        "/api/v1/cart/items", {"product": "missing-slug"}, format="json"
    )
    assert response.status_code == 404


def test_user_cart_is_separate_from_guest(api_client, user, product, store):
    api_client = APIClient(headers={"X-Store": store.slug})
    api_client.force_authenticate(user=user)
    response = api_client.post(
        "/api/v1/cart/items", {"product": product.slug}, format="json"
    )
    assert response.status_code == 201, response.data
    cart = get_or_create_cart(store, user=user)
    assert cart.items.count() == 1


def test_checkout_creates_order_from_cart(api_client, user, store, product):
    ensure_default_payment_methods()
    from apps.checkout.models import ShippingMethod

    ShippingMethod.objects.create(
        store=store, name="Post", code="POST", flat_price=Decimal("4.0000")
    )
    api_client = APIClient(headers={"X-Store": store.slug})
    api_client.force_authenticate(user=user)
    api_client.post("/api/v1/cart/items", {"product": product.slug, "quantity": 2}, format="json")

    response = api_client.post(
        "/api/v1/checkout",
        {
            "shipping_address": ADDRESS,
            "shipping_method_code": "POST",
            "payment_method_code": "cash_on_delivery",
        },
        format="json",
    )
    assert response.status_code == 201
    assert response.data["total"] == "24.0000"
    assert response.data["status"] == "pending"


def test_checkout_requires_shipping_method(api_client, user, product, store):
    ensure_default_payment_methods()
    api_client = APIClient(headers={"X-Store": store.slug})
    api_client.force_authenticate(user=user)
    api_client.post("/api/v1/cart/items", {"product": product.slug}, format="json")
    response = api_client.post(
        "/api/v1/checkout",
        {
            "shipping_address": ADDRESS,
            "shipping_method_code": "NOPE",
            "payment_method_code": "cash_on_delivery",
        },
        format="json",
    )
    assert response.status_code == 404


def test_checkout_methods_lists_store_options(api_client, store):
    ensure_default_payment_methods()
    from apps.checkout.models import ShippingMethod

    ShippingMethod.objects.create(
        store=store, name="Post", code="POST", flat_price=Decimal("4.0000")
    )
    response = api_client.get("/api/v1/checkout/methods", {"store": store.slug})
    assert response.status_code == 200
    codes = {method["code"] for method in response.data["shipping_methods"]}
    assert "POST" in codes
    assert any(method["code"] == "cash_on_delivery" for method in response.data["payment_methods"])
