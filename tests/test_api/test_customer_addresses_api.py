from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.catalog.services import create_product, publish_product
from apps.checkout.models import ShippingMethod, ensure_default_payment_methods
from apps.identity.models import Address, Customer
from apps.orders.models import Order, OrderAddress
from apps.stores.services import create_store

pytestmark = [pytest.mark.django_db]

PASSWORD = "Str0ng!Passw0rd"

ADDRESS = {
    "first_name": "Ali",
    "last_name": "Rezaei",
    "email": "ali@example.com",
    "phone": "+989121234567",
    "country": "IR",
    "state": "Tehran",
    "city": "Tehran",
    "postal_code": "1234567890",
    "address_line": "Valiasr St. 10",
}


def make_customer(email: str):
    user = get_user_model().objects.create_user(email=email, password=PASSWORD)
    Customer.objects.create(user=user)
    return user


@pytest.fixture
def owner(db):
    return make_customer("owner@example.com")


@pytest.fixture
def other(db):
    return make_customer("other@example.com")


@pytest.fixture
def owner_client(api_client, owner):
    client = APIClient()
    client.force_authenticate(user=owner)
    return client


@pytest.fixture
def other_client(api_client, other):
    client = APIClient()
    client.force_authenticate(user=other)
    return client


def create_address(client, **overrides):
    payload = {**ADDRESS, **overrides}
    return client.post("/api/v1/customers/me/addresses", payload, format="json")


def test_customer_creates_and_lists_own_addresses(owner_client, owner):
    response = create_address(owner_client)
    assert response.status_code == 201, response.data
    assert response.data["address_line"] == ADDRESS["address_line"]
    assert response.data["is_default"] is False

    listing = owner_client.get("/api/v1/customers/me/addresses")
    assert listing.status_code == 200
    assert len(listing.data) == 1
    assert listing.data[0]["id"] == response.data["id"]


def test_address_creation_requires_mandatory_fields(owner_client):
    response = owner_client.post(
        "/api/v1/customers/me/addresses", {"city": "Tehran"}, format="json"
    )
    assert response.status_code == 400
    details = response.data["error"]["details"]
    for field in ("country", "address_line"):
        assert field in details
    assert "city" not in details


def test_addresses_require_authentication(api_client):
    assert api_client.get("/api/v1/customers/me/addresses").status_code in (401, 403)
    assert create_address(api_client).status_code in (401, 403)


def test_customer_cannot_read_or_change_another_customers_address(owner_client, other_client):
    created = create_address(other_client)
    assert created.status_code == 201
    address_id = created.data["id"]

    assert owner_client.get(f"/api/v1/customers/me/addresses/{address_id}").status_code == 404
    assert (
        owner_client.patch(
            f"/api/v1/customers/me/addresses/{address_id}", {"city": "Elsewhere"}, format="json"
        ).status_code
        == 404
    )
    assert owner_client.delete(f"/api/v1/customers/me/addresses/{address_id}").status_code == 404

    listing = owner_client.get("/api/v1/customers/me/addresses")
    assert listing.data == []
    # The other customer's address is untouched.
    assert Address.objects.filter(pk=address_id, is_deleted=False).exists()


def test_only_one_default_address_per_customer(owner_client):
    first = create_address(owner_client, is_default=True)
    second = create_address(owner_client, is_default=True)

    assert first.status_code == 201
    assert second.status_code == 201
    assert Address.objects.get(pk=first.data["id"]).is_default is False
    assert Address.objects.get(pk=second.data["id"]).is_default is True


def test_default_can_be_moved_to_another_address(owner_client):
    first = create_address(owner_client, is_default=True)
    second = create_address(owner_client)

    response = owner_client.patch(
        f"/api/v1/customers/me/addresses/{second.data['id']}",
        {"is_default": True},
        format="json",
    )
    assert response.status_code == 200
    assert response.data["is_default"] is True
    assert Address.objects.get(pk=first.data["id"]).is_default is False


def test_customer_can_update_and_delete_own_address(owner_client):
    created = create_address(owner_client)
    address_id = created.data["id"]

    response = owner_client.patch(
        f"/api/v1/customers/me/addresses/{address_id}",
        {"address_line": "Updated St. 2"},
        format="json",
    )
    assert response.status_code == 200
    assert response.data["address_line"] == "Updated St. 2"

    assert owner_client.delete(f"/api/v1/customers/me/addresses/{address_id}").status_code == 204
    assert owner_client.get("/api/v1/customers/me/addresses").data == []
    # Soft delete: the row is retained but no longer part of the address book.
    assert Address.all_objects.filter(pk=address_id, is_deleted=True).exists()


@pytest.fixture
def store(db):
    return create_store("Address API Store")


@pytest.fixture
def product(db, store):
    product = create_product(store, "Address API Product", price=Decimal("10.0000"), stock_quantity=10)
    publish_product(product)
    return product


def checkout_client(api_client, store, owner):
    client = APIClient(headers={"X-Store": store.slug})
    client.force_authenticate(user=owner)
    return client


def test_checkout_copies_a_saved_address_into_the_order_snapshot(api_client, owner, store, product):
    ensure_default_payment_methods()
    ShippingMethod.objects.create(
        store=store, name="Post", code="POST", flat_price=Decimal("4.0000")
    )
    client = checkout_client(api_client, store, owner)
    created = create_address(client)
    assert created.status_code == 201

    client.post("/api/v1/cart/items", {"product": product.slug, "quantity": 1}, format="json")
    response = client.post(
        "/api/v1/checkout",
        {
            "shipping_address_id": created.data["id"],
            "shipping_method_code": "POST",
            "payment_method_code": "cash_on_delivery",
        },
        format="json",
    )
    assert response.status_code == 201, response.data

    order = Order.objects.get(number=response.data["order_number"])
    snapshot = OrderAddress.objects.get(order=order)
    assert snapshot.address_line == ADDRESS["address_line"]
    assert snapshot.city == ADDRESS["city"]
    assert snapshot.country == ADDRESS["country"]
    assert snapshot.email == ADDRESS["email"]


def test_checkout_rejects_another_customers_saved_address(api_client, owner, other, store, product):
    ensure_default_payment_methods()
    ShippingMethod.objects.create(
        store=store, name="Post", code="POST", flat_price=Decimal("4.0000")
    )
    foreign = create_address(checkout_client(api_client, store, other))
    assert foreign.status_code == 201

    client = checkout_client(api_client, store, owner)
    client.post("/api/v1/cart/items", {"product": product.slug, "quantity": 1}, format="json")
    response = client.post(
        "/api/v1/checkout",
        {
            "shipping_address_id": foreign.data["id"],
            "shipping_method_code": "POST",
            "payment_method_code": "cash_on_delivery",
        },
        format="json",
    )
    assert response.status_code == 404
    assert Order.objects.count() == 0


def test_checkout_with_a_saved_address_requires_authentication(api_client, store, product):
    ensure_default_payment_methods()
    ShippingMethod.objects.create(
        store=store, name="Post", code="POST", flat_price=Decimal("4.0000")
    )
    guest = APIClient(headers={"X-Store": store.slug, "X-Cart-Session": "guest-address"})
    guest.post("/api/v1/cart/items", {"product": product.slug, "quantity": 1}, format="json")
    response = guest.post(
        "/api/v1/checkout",
        {
            "shipping_address_id": 1,
            "shipping_method_code": "POST",
            "payment_method_code": "cash_on_delivery",
        },
        format="json",
    )
    assert response.status_code == 400
    assert response.data["error"]["code"] == "checkout.address_requires_authentication"
    assert Order.objects.count() == 0


def test_changing_a_saved_address_does_not_change_an_existing_order_snapshot(
    api_client, owner, store, product
):
    ensure_default_payment_methods()
    ShippingMethod.objects.create(
        store=store, name="Post", code="POST", flat_price=Decimal("4.0000")
    )
    client = checkout_client(api_client, store, owner)
    created = create_address(client)
    client.post("/api/v1/cart/items", {"product": product.slug, "quantity": 1}, format="json")
    response = client.post(
        "/api/v1/checkout",
        {
            "shipping_address_id": created.data["id"],
            "shipping_method_code": "POST",
            "payment_method_code": "cash_on_delivery",
        },
        format="json",
    )
    assert response.status_code == 201, response.data
    order = Order.objects.get(number=response.data["order_number"])

    client.patch(
        f"/api/v1/customers/me/addresses/{created.data['id']}",
        {"address_line": "Completely different St. 99"},
        format="json",
    )
    client.delete(f"/api/v1/customers/me/addresses/{created.data['id']}")

    snapshot = OrderAddress.objects.get(order=order)
    assert snapshot.address_line == ADDRESS["address_line"]


def test_staff_admin_can_view_but_not_edit_addresses():
    from apps.admin_panel.admin_site import admin_site

    admin = admin_site._registry[Address]
    assert admin.has_add_permission(None) is False
    assert admin.has_change_permission(None) is False
    assert admin.has_delete_permission(None) is False
