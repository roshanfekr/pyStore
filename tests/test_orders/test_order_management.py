from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.cart.services import add_to_cart, get_or_create_cart
from apps.catalog.services import add_variant, create_product, publish_product
from apps.checkout.models import ShippingMethod
from apps.checkout.services import execute_checkout
from apps.inventory.services import create_warehouse, get_or_create_inventory, receive_stock
from apps.orders.models import (
    Order,
    OrderItem,
    OrderStatusLog,
    ReturnRequest,
)
from apps.orders.services import (
    add_order_note,
    approve_return,
    cancel_order,
    cancel_order_items,
    ensure_order_permissions,
    issue_invoice,
    order_notes,
    receive_return,
    refund_order,
    refund_order_item,
    refundable_amount,
    reject_return,
    request_return,
    set_payment_status,
    set_shipment_status,
    transition_order_status,
)
from apps.orders.state_machine import OrderStateMachine
from apps.stores.services import create_store
from core.exceptions import ValidationError

User = get_user_model()

pytestmark = [pytest.mark.django_db]

PRICE = Decimal("100.0000")


@pytest.fixture
def store(db):
    return create_store("OM Store")


@pytest.fixture
def staff(db):
    return User.objects.create_user(email="staffom@example.com", password="Str0ng!Passw0rd")


@pytest.fixture
def customer(db):
    return User.objects.create_user(email="omcustomer@example.com", password="Str0ng!Passw0rd")


@pytest.fixture
def shipping_method(db, store):
    return ShippingMethod.objects.create(
        store=store, name="Post", code="POST", flat_price=Decimal("5.0000")
    )


@pytest.fixture
def payment_methods(db):
    from apps.checkout.models import ensure_default_payment_methods

    ensure_default_payment_methods()


ADDRESS = {"country": "IR", "state": "TEH", "city": "Tehran", "address_line": "Somewhere 1"}


@pytest.fixture
def order(store, customer, shipping_method, payment_methods):
    product = create_product(store, "OM Product", price=PRICE, stock_quantity=100)
    publish_product(product)
    cart = get_or_create_cart(store, user=customer)
    add_to_cart(cart, product, 2)

    return execute_checkout(
        cart,
        user=customer,
        shipping_address=dict(ADDRESS),
        shipping_method_code="POST",
        payment_method_code="cash_on_delivery",
    )


def _mark_paid(order):
    transition_order_status(order, Order.STATUS_PROCESSING)
    set_payment_status(order, Order.PAYMENT_PAID)
    transition_order_status(order, Order.STATUS_PAID)
    return order


def test_order_lifecycle_transitions(order, staff):
    transition_order_status(order, Order.STATUS_PROCESSING, actor=staff)
    transition_order_status(order, Order.STATUS_PAID, actor=staff)
    transition_order_status(order, Order.STATUS_SHIPPED, actor=staff)
    transition_order_status(order, Order.STATUS_COMPLETED, actor=staff)

    order.refresh_from_db()
    assert order.status == Order.STATUS_COMPLETED
    logs = OrderStatusLog.objects.filter(order=order, status_type="order")
    assert logs.count() == 4


def test_invalid_transition_rejected(order):
    with pytest.raises(ValidationError, match="not allowed"):
        transition_order_status(order, Order.STATUS_COMPLETED)


def test_state_machine_is_extensible():
    OrderStateMachine.register_status("awaiting_pickup", {"shipped"})
    OrderStateMachine.register_transition("processing", "awaiting_pickup")
    try:
        assert OrderStateMachine.can_transition("processing", "awaiting_pickup")
        assert OrderStateMachine.can_transition("awaiting_pickup", "shipped")
        assert not OrderStateMachine.can_transition("awaiting_pickup", "paid")
    finally:
        OrderStateMachine.reset()

    assert not OrderStateMachine.can_transition("processing", "awaiting_pickup")


def test_payment_status_transitions(order):
    set_payment_status(order, Order.PAYMENT_FAILED)
    set_payment_status(order, Order.PAYMENT_PENDING)
    set_payment_status(order, Order.PAYMENT_PAID)

    with pytest.raises(ValidationError):
        set_payment_status(order, Order.PAYMENT_PENDING)

    set_payment_status(order, Order.PAYMENT_REFUNDED)
    order.refresh_from_db()
    assert order.payment_status == Order.PAYMENT_REFUNDED


def test_shipment_status_transitions(order):
    with pytest.raises(ValidationError):
        set_shipment_status(order, Order.SHIPMENT_DELIVERED)

    set_shipment_status(order, Order.SHIPMENT_SHIPPED)
    set_shipment_status(order, Order.SHIPMENT_DELIVERED)
    order.refresh_from_db()
    assert order.shipment_status == Order.SHIPMENT_DELIVERED


def test_cancel_order_restocks_fallback_stock(order, store):
    product = OrderItem.objects.get(order=order).product
    cancel_order(order)

    order.refresh_from_db()
    assert order.status == Order.STATUS_CANCELLED
    product.refresh_from_db()
    assert product.stock_quantity == 100
    assert order.items.first().remaining_quantity == 0


def test_cancelled_order_cannot_transition(order):
    cancel_order(order)
    with pytest.raises(ValidationError):
        transition_order_status(order, Order.STATUS_PROCESSING)


def test_partial_cancellation(order, store):
    item = order.items.first()
    cancel_order_items(order, {item.id: 1}, note="One unit cancelled")

    item.refresh_from_db()
    order.refresh_from_db()
    assert item.remaining_quantity == 1
    assert order.subtotal == Decimal("100.0000")
    assert order.total == Decimal("105.0000")
    assert order.status == Order.STATUS_PENDING


def test_refund_full_flow(order):
    _mark_paid(order)

    refund = refund_order(order, Decimal("205.0000"), reason="customer changed mind")

    order.refresh_from_db()
    assert refund.amount == Decimal("205.0000")
    assert order.payment_status == Order.PAYMENT_REFUNDED
    assert order.status == Order.STATUS_REFUNDED
    assert refundable_amount(order) == Decimal("0.0000")


def test_refund_partial(order):
    _mark_paid(order)

    refund_order(order, Decimal("50.0000"), reason="partial refund")

    order.refresh_from_db()
    assert order.payment_status == Order.PAYMENT_PAID
    assert order.status == Order.STATUS_PAID
    assert refundable_amount(order) == Decimal("155.0000")


def test_refund_requires_paid_payment_status(order):
    with pytest.raises(ValidationError, match="paid"):
        refund_order(order, Decimal("10.0000"))


def test_refund_exceeding_balance_rejected(order):
    _mark_paid(order)
    with pytest.raises(ValidationError, match="refundable"):
        refund_order(order, Decimal("999.0000"))


def test_refund_order_item(order):
    _mark_paid(order)
    item = order.items.first()

    refund = refund_order_item(item, 1, reason="damaged unit")

    assert refund.amount == Decimal("100.0000")
    assert refund.order_item_id == item.id
    assert refundable_amount(order) == Decimal("105.0000")


def test_order_notes_internal_and_customer(order, staff, customer):
    add_order_note(order, "Internal: verify stock", note_type="internal", author=staff)
    add_order_note(order, "Please deliver fast", note_type="customer", author=customer)

    all_notes = order_notes(order)
    customer_only = order_notes(order, include_internal=False)

    assert all_notes.count() == 2
    assert customer_only.count() == 1
    assert customer_only.first().note_type == "customer"


def test_note_requires_text(order):
    with pytest.raises(ValidationError):
        add_order_note(order, "   ")


def test_invoice_issue(order):
    from core.exceptions import ConflictError

    assert order.invoice_number is None

    issue_invoice(order)
    assert order.invoice_number.startswith("INV-")
    assert order.invoice_date is not None

    with pytest.raises(ConflictError, match="already"):
        issue_invoice(order)


def test_return_flow_with_restock(order, customer):
    _mark_paid(order)
    item = order.items.first()

    return_request = request_return(
        order, [(item, 1)], user=customer, reason="size mismatch"
    )
    assert return_request.status == ReturnRequest.STATUS_REQUESTED

    approve_return(return_request)
    return_request.refresh_from_db()
    assert return_request.status == ReturnRequest.STATUS_APPROVED

    receive_return(return_request)
    return_request.refresh_from_db()
    assert return_request.status == ReturnRequest.STATUS_RECEIVED


def test_return_requires_valid_status(order, customer):
    item = order.items.first()
    with pytest.raises(ValidationError, match="not allowed"):
        request_return(order, [(item, 1)], user=customer, reason="nope")


def test_return_rejection(order, customer):
    _mark_paid(order)
    item = order.items.first()
    return_request = request_return(order, [(item, 1)], user=customer, reason="x")

    reject_return(return_request)
    return_request.refresh_from_db()
    assert return_request.status == ReturnRequest.STATUS_REJECTED

    with pytest.raises(ValidationError):
        approve_return(return_request)


def test_return_quantity_validation(order, customer):
    _mark_paid(order)
    item = order.items.first()
    with pytest.raises(ValidationError):
        request_return(order, [(item, 5)], user=customer, reason="too many")


def test_order_permissions_declared(db):
    from apps.identity.models import Permission

    ensure_order_permissions()
    for code in ["order.view", "order.cancel", "order.refund", "order.edit"]:
        assert Permission.objects.filter(codename=code, source="core").exists()


def test_cancel_releases_inventory_reservation(store, customer, shipping_method, payment_methods):
    product = create_product(store, "OM Variant Thing", product_type="variant")
    variant = add_variant(product, "OMV-1", Decimal("20.0000"))
    publish_product(product)

    warehouse = create_warehouse(store, "OM WH", "WH-OM")
    item = get_or_create_inventory(warehouse, variant=variant)
    receive_stock(item, 10)

    cart = get_or_create_cart(store, user=customer)
    add_to_cart(cart, product, 4, variant=variant)
    order = execute_checkout(
        cart,
        user=customer,
        shipping_address=dict(ADDRESS),
        shipping_method_code="POST",
        payment_method_code="cash_on_delivery",
    )

    item.refresh_from_db()
    assert item.reserved_quantity == 4

    cancel_order(order)

    item.refresh_from_db()
    assert item.reserved_quantity == 0
    assert item.available_quantity == 10
