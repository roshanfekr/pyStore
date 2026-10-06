from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.cart.services import add_to_cart, get_or_create_cart
from apps.catalog.services import create_product, publish_product
from apps.checkout.services import execute_checkout
from apps.orders.models import Order
from apps.orders.services import set_payment_status, transition_order_status
from apps.stores.services import create_store

pytestmark = [pytest.mark.django_db]

ADDRESS = {"country": "IR", "city": "Tehran", "address_line": "Test 1"}


@pytest.fixture
def env(db):
    store = create_store("Orders API Store")
    product = create_product(store, "Orders Product", price=Decimal("10.0000"), stock_quantity=10)
    publish_product(product)
    return store, product


def make_order(env, email: str) -> Order:
    from apps.checkout.models import ShippingMethod, ensure_default_payment_methods

    store, product = env
    ensure_default_payment_methods()
    ShippingMethod.objects.create(
        store=store, name="Post", code="POST", flat_price=Decimal("2.0000")
    )
    cart = get_or_create_cart(store, session_key=email)
    add_to_cart(cart, product, 1)
    return execute_checkout(
        cart,
        user=None,
        email=email,
        shipping_address=ADDRESS,
        shipping_method_code="POST",
        payment_method_code="cash_on_delivery",
    )


def test_order_access_scoping(api_client, env, db):
    from django.contrib.auth import get_user_model

    User = get_user_model()
    owner = User.objects.create_user(email="owner@example.com", password="Str0ng!Passw0rd")
    other = User.objects.create_user(email="other@example.com", password="Str0ng!Passw0rd")

    store, product = env
    from apps.checkout.models import ShippingMethod, ensure_default_payment_methods

    ensure_default_payment_methods()
    ShippingMethod.objects.create(
        store=store, name="Post", code="POST", flat_price=Decimal("2.0000")
    )
    cart = get_or_create_cart(store, user=owner)
    add_to_cart(cart, product, 1)
    order = execute_checkout(
        cart,
        user=owner,
        shipping_address=ADDRESS,
        shipping_method_code="POST",
        payment_method_code="cash_on_delivery",
    )

    client = APIClient()
    client.force_authenticate(user=owner)
    response = client.get("/api/v1/orders")
    assert response.data["count"] == 1

    client.force_authenticate(user=other)
    response = client.get("/api/v1/orders")
    assert response.data["count"] == 0
    assert client.get(f"/api/v1/orders/{order.number}").status_code == 404


def test_order_detail_by_number(api_client, env, db):
    order = make_order(env, "detail@example.com")
    response = api_client.get(f"/api/v1/orders/{order.number}")
    assert response.status_code == 401


def test_order_cancel_action(api_client, env, db):
    from django.contrib.auth import get_user_model


    User = get_user_model()
    user = User.objects.create_user(email="cancel@example.com", password="Str0ng!Passw0rd")
    store, product = env
    from apps.checkout.models import ShippingMethod, ensure_default_payment_methods

    ensure_default_payment_methods()
    ShippingMethod.objects.create(
        store=store, name="Post", code="POST", flat_price=Decimal("2.0000")
    )
    cart = get_or_create_cart(store, user=user)
    add_to_cart(cart, product, 1)
    order = execute_checkout(
        cart,
        user=user,
        shipping_address=ADDRESS,
        shipping_method_code="POST",
        payment_method_code="cash_on_delivery",
    )

    client = APIClient()
    client.force_authenticate(user=user)
    response = client.post(f"/api/v1/orders/{order.number}/cancel", {"note": "changed mind"}, format="json")
    assert response.status_code == 200
    assert response.data["status"] == Order.STATUS_CANCELLED

    order.refresh_from_db()
    assert order.status == Order.STATUS_CANCELLED


def test_order_return_request(api_client, env, db):
    from django.contrib.auth import get_user_model

    User = get_user_model()
    user = User.objects.create_user(email="returner@example.com", password="Str0ng!Passw0rd")
    store, product = env
    from apps.checkout.models import ShippingMethod, ensure_default_payment_methods

    ensure_default_payment_methods()
    ShippingMethod.objects.create(
        store=store, name="Post", code="POST", flat_price=Decimal("2.0000")
    )
    cart = get_or_create_cart(store, user=user)
    add_to_cart(cart, product, 2)
    order = execute_checkout(
        cart,
        user=user,
        shipping_address=ADDRESS,
        shipping_method_code="POST",
        payment_method_code="cash_on_delivery",
    )
    transition_to_paid(order)

    client = APIClient()
    client.force_authenticate(user=user)
    item = order.items.first()
    response = client.post(
        f"/api/v1/orders/{order.number}/returns",
        {"items": [{"order_item_id": str(item.id), "quantity": 1}], "reason": "broken"},
        format="json",
    )
    assert response.status_code == 201, response.data
    assert response.data["status"] == "requested"


def transition_to_paid(order):
    transition_order_status(order, Order.STATUS_PROCESSING)
    set_payment_status(order, Order.PAYMENT_PAID)
    transition_order_status(order, Order.STATUS_PAID)
    return order


def test_payment_initialize_with_registered_gateway(api_client, env, db):
    from django.contrib.auth import get_user_model

    from core.payments.interface import PaymentGateway
    from core.payments.registry import payment_gateway_registry

    class StubGateway(PaymentGateway):
        code = "cash_on_delivery"
        name = "Stub"

        def initialize_payment(self, order, **kwargs):
            from core.payments.interface import PaymentResult

            return PaymentResult(successful=True, reference="stub-1")

        def authorize(self, order, **kwargs):
            from core.payments.interface import PaymentResult

            return PaymentResult(successful=True)

        def capture(self, order, **kwargs):
            from core.payments.interface import PaymentResult

            return PaymentResult(successful=True)

        def void(self, order, **kwargs):
            from core.payments.interface import PaymentResult

            return PaymentResult(successful=True)

        def refund(self, order, amount, **kwargs):
            from core.payments.interface import PaymentResult

            return PaymentResult(successful=True)

    User = get_user_model()
    user = User.objects.create_user(email="payer@example.com", password="Str0ng!Passw0rd")
    order = make_order(env, "payer@example.com")
    order.user = user
    order.save(update_fields=["user"])

    payment_gateway_registry.register(StubGateway())
    try:
        client = APIClient()
        client.force_authenticate(user=user)
        response = client.post(
            "/api/v1/payments/initialize", {"order": order.number}, format="json"
        )
        assert response.status_code == 200
        assert response.data["reference"] == "stub-1"
    finally:
        payment_gateway_registry.unregister("cash_on_delivery")


def test_payment_initialize_requires_auth(api_client, env, db):
    order = make_order(env, "anonpay@example.com")
    response = api_client.post(
        "/api/v1/payments/initialize", {"order": order.number}, format="json"
    )
    assert response.status_code == 401


def test_shipping_methods_and_rates(api_client, env, db):
    from apps.checkout.models import ShippingMethod
    from core.shipping.interface import ShippingProvider
    from core.shipping.registry import shipping_provider_registry

    store, _ = env
    ShippingMethod.objects.create(
        store=store, name="Post", code="POST", flat_price=Decimal("3.0000")
    )
    response = api_client.get("/api/v1/shipping/methods", {"store": store.slug})
    assert response.status_code == 200
    assert response.data[0]["code"] == "POST"

    class StubProvider(ShippingProvider):
        code = "stub_ship"
        name = "Stub Ship"

        def get_rates(self, context):
            return [{"code": "flat", "name": "Flat", "price": Decimal("3.0000")}]

        def calculate_shipping(self, context):
            return Decimal("3.0000")

        def create_shipment(self, order, **kwargs):
            return {"tracking_number": "TRK-1"}

        def cancel_shipment(self, shipment_id, **kwargs):
            return {"cancelled": True}

        def get_tracking(self, tracking_number):
            return {"status": "in_transit", "tracking_number": tracking_number}

    shipping_provider_registry.register(StubProvider())
    try:
        response = api_client.post(
            "/api/v1/shipping/rates",
            {"provider_code": "stub_ship", "context": {"country": "IR"}},
            format="json",
        )
        assert response.status_code == 200
        assert response.data["rates"][0]["code"] == "flat"

        response = api_client.post(
            "/api/v1/shipping/track",
            {"provider_code": "stub_ship", "tracking_number": "TRK-9"},
            format="json",
        )
        assert response.status_code == 200
        assert response.data["tracking"]["status"] == "in_transit"
    finally:
        shipping_provider_registry.unregister("stub_ship")
