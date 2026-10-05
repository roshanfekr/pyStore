from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.cart.services import add_to_cart, get_or_create_cart
from apps.catalog.services import create_product, publish_product
from apps.checkout.models import PaymentMethod, ShippingMethod
from apps.checkout.plugins_sync import (
    deactivate_provider_shipping_methods,
    sync_payment_methods,
    sync_shipping_methods,
)
from apps.checkout.services import execute_checkout
from apps.orders.models import Order
from apps.stores.services import create_store
from core.payments import PaymentResult, payment_gateway_registry
from core.payments.interface import PaymentGateway
from core.plugins.manager import PluginManager
from core.shipping import shipping_provider_registry
from core.shipping.interface import ShippingProvider

User = get_user_model()

pytestmark = [pytest.mark.django_db]

ADDRESS = {"country": "IR", "city": "Tehran", "address_line": "Test 1"}


@pytest.fixture
def manager(db):
    manager = PluginManager()
    manager.discover_plugins()
    return manager


@pytest.fixture
def enabled_plugins(manager):
    for plugin_id in ("payment_dummy", "shipping_dummy"):
        if PluginState_exists(manager, plugin_id):
            manager.enable_plugin(plugin_id)
        else:
            manager.install_plugin(plugin_id)
            manager.enable_plugin(plugin_id)
    yield manager
    for plugin_id in ("payment_dummy", "shipping_dummy"):
        try:
            manager.disable_plugin(plugin_id)
        except Exception:
            pass


def PluginState_exists(manager, plugin_id):
    from core.plugins.models import PluginState

    return PluginState.objects.filter(plugin_id=plugin_id).exists()


@pytest.fixture
def store(db):
    return create_store("Gateway Store")


def test_payment_gateway_interface_contract():
    class MinimalGateway(PaymentGateway):
        code = "mini"
        name = "Mini"

        def initialize_payment(self, order, **kwargs):
            return PaymentResult(successful=True, reference="r1")

        def authorize(self, order, **kwargs):
            return PaymentResult(successful=True, reference="r2")

        def capture(self, order, **kwargs):
            return PaymentResult(successful=True, reference="r3")

        def void(self, order, **kwargs):
            return PaymentResult(successful=True, reference="r4")

        def refund(self, order, amount, **kwargs):
            return PaymentResult(successful=True, reference="r5")

    gateway = MinimalGateway()
    assert gateway.supports("anything") is False
    gateway.SUPPORTED_FEATURES = ("authorize",)
    assert gateway.supports("authorize") is True
    assert gateway.get_configuration() == {}

    gateway.configure({"key": "val"})
    assert gateway.get_configuration() == {"key": "val"}

    result = gateway.authorize(None)
    assert result.successful and result.reference == "r2"


def test_payment_registry_register_and_unregister():
    class TempGateway(PaymentGateway):
        code = "temp"
        name = "Temp"

        def initialize_payment(self, order, **kwargs):
            return PaymentResult(successful=True)

        def authorize(self, order, **kwargs):
            return PaymentResult(successful=True)

        def capture(self, order, **kwargs):
            return PaymentResult(successful=True)

        def void(self, order, **kwargs):
            return PaymentResult(successful=True)

        def refund(self, order, amount, **kwargs):
            return PaymentResult(successful=True)

    gateway = TempGateway()
    payment_gateway_registry.register(gateway)
    assert payment_gateway_registry.get("temp") is gateway

    payment_gateway_registry.unregister("temp")
    assert payment_gateway_registry.get("temp") is None


def test_shipping_provider_contract():
    class TempProvider(ShippingProvider):
        code = "temp_ship"
        name = "Temp Ship"

        def get_rates(self, context):
            return [{"code": "t1", "name": "T1", "price": Decimal("3.0000")}]

        def calculate_shipping(self, context):
            return Decimal("3.0000")

        def create_shipment(self, order, **kwargs):
            return {"tracking_number": "T-1"}

        def cancel_shipment(self, shipment_id, **kwargs):
            return {"cancelled": True}

        def get_tracking(self, tracking_number):
            return {"status": "in_transit"}

    provider = TempProvider()
    assert provider.get_rates({})[0]["code"] == "t1"
    assert provider.calculate_shipping({}) == Decimal("3.0000")
    assert provider.create_shipment(None)["tracking_number"] == "T-1"
    assert provider.cancel_shipment("x") == {"cancelled": True}
    assert provider.get_tracking("T-1")["status"] == "in_transit"


def test_dummy_plugins_discovered(manager):
    assert "payment_dummy" in manager.discover_plugins()
    assert "shipping_dummy" in manager.discover_plugins()


def test_dummy_gateway_operations(enabled_plugins):
    from plugins.payment_dummy.gateway import DummyGateway

    gateway = payment_gateway_registry.get("payment_dummy")
    assert isinstance(gateway, DummyGateway)

    init = gateway.initialize_payment(None, amount=Decimal("10.0000"))
    assert init.successful is True
    assert init.raw["redirect_url"].startswith("https://dummy.example/pay/")

    assert gateway.authorize(None).successful
    assert gateway.capture(None, amount=Decimal("10.0000")).successful
    assert gateway.void(None).successful
    assert gateway.refund(None, Decimal("5.0000")).raw["refunded_amount"] == "5.0000"

    assert gateway.supports("refund") is True
    assert gateway.supports("installments") is False

    assert gateway.get_configuration()["merchant_id"] == "dummy-merchant"


def test_dummy_provider_operations():
    from plugins.shipping_dummy.provider import DummyShippingProvider

    provider = DummyShippingProvider()
    rates = provider.get_rates({})
    assert {r["code"] for r in rates} == {"dummy_standard", "dummy_express"}
    assert provider.calculate_shipping({"code": "dummy_express"}) == Decimal("15.0000")

    shipment = provider.create_shipment(None)
    assert shipment["tracking_number"].startswith("DUMMY-")
    assert provider.cancel_shipment(shipment["tracking_number"])["cancelled"] is True
    assert provider.get_tracking("DUMMY-X")["status"] == "in_transit"


def test_enable_registers_gateways_and_providers(enabled_plugins):
    assert payment_gateway_registry.get("payment_dummy") is not None
    assert shipping_provider_registry.get("shipping_dummy") is not None


def test_disable_unregisters_gateways_and_providers(manager):
    if PluginState_exists(manager, "payment_dummy"):
        manager.enable_plugin("payment_dummy")
    else:
        manager.install_plugin("payment_dummy")
        manager.enable_plugin("payment_dummy")
    assert payment_gateway_registry.get("payment_dummy") is not None

    manager.disable_plugin("payment_dummy")
    assert payment_gateway_registry.get("payment_dummy") is None


def test_admin_can_configure_gateway_via_plugin_settings(enabled_plugins, manager):
    manager.set_settings("payment_dummy", {"merchant_id": "admin-merchant-42"})

    manager.disable_plugin("payment_dummy")
    manager.enable_plugin("payment_dummy")

    gateway = payment_gateway_registry.get("payment_dummy")
    config = gateway.get_configuration()
    assert config["merchant_id"] == "admin-merchant-42"


def test_sync_payment_methods_creates_rows(enabled_plugins):
    created = sync_payment_methods()
    assert created == 1
    method = PaymentMethod.objects.get(code="payment_dummy")
    assert method.name == "Dummy Payment Gateway"
    assert method.is_active is True


def test_sync_shipping_methods_for_store(enabled_plugins, store):
    created = sync_shipping_methods(store)

    assert created == 2
    codes = set(ShippingMethod.objects.filter(store=store).values_list("code", flat=True))
    assert {"dummy_standard", "dummy_express"} <= codes

    express = ShippingMethod.objects.get(store=store, code="dummy_express")
    assert express.flat_price == Decimal("15.0000")
    assert express.provider_code == "shipping_dummy"


def test_deactivate_provider_methods_on_disable(enabled_plugins, store, manager):
    sync_shipping_methods(store)
    manager.disable_plugin("shipping_dummy")
    deactivate_provider_shipping_methods("shipping_dummy")

    method = ShippingMethod.objects.get(store=store, code="dummy_standard")
    assert method.is_active is False


def test_dummy_plugins_usable_in_checkout(enabled_plugins, store):
    from django.contrib.auth import get_user_model as gUM

    sync_payment_methods()
    sync_shipping_methods(store)

    user = gUM().objects.create_user(email="dummybuyer@example.com", password="Str0ng!Passw0rd")
    product = create_product(store, "Dummy Checkout Product", price=Decimal("50.0000"), stock_quantity=10)
    publish_product(product)

    cart = get_or_create_cart(store, user=user)
    add_to_cart(cart, product, 2)

    order = execute_checkout(
        cart,
        user=user,
        shipping_address=ADDRESS,
        shipping_method_code="dummy_standard",
        payment_method_code="payment_dummy",
    )

    assert order.payment_method == "payment_dummy"
    assert order.shipping_method == "dummy_standard"
    assert order.shipping_amount == Decimal("5.0000")
    assert order.subtotal == Decimal("100.0000")
    assert order.total == Decimal("105.0000")
    assert order.status == Order.STATUS_PENDING
