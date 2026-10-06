from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core import mail

from apps.cart.services import add_to_cart, get_or_create_cart
from apps.catalog.services import create_product, publish_product
from apps.checkout.models import ensure_default_payment_methods
from apps.checkout.services import execute_checkout
from apps.notifications.models import Notification, NotificationMessage
from apps.orders.models import Order
from apps.orders.services import set_payment_status, transition_order_status
from apps.stores.services import create_store

User = get_user_model()

pytestmark = [pytest.mark.django_db]

ADDRESS = {"country": "IR", "city": "Tehran", "address_line": "Test 1"}


@pytest.fixture
def sync_delivery(db):
    from core.settings.service import settings_service

    settings_service.set("notifications", "async_delivery", False)
    yield
    settings_service.set("notifications", "async_delivery", True)


@pytest.fixture
def checkout_order(db, sync_delivery):
    store = create_store("Notif Checkout Store")
    ensure_default_payment_methods()
    from apps.checkout.models import ShippingMethod

    ShippingMethod.objects.create(
        store=store, name="Post", code="POST", flat_price=Decimal("5.0000")
    )
    product = create_product(store, "Notif Product", price=Decimal("20.0000"), stock_quantity=10)
    publish_product(product)
    user = User.objects.create_user(email="flowbuyer@example.com", password="Str0ng!Passw0rd")
    cart = get_or_create_cart(store, user=user)
    add_to_cart(cart, product, 1)
    order = execute_checkout(
        cart,
        user=user,
        shipping_address=ADDRESS,
        shipping_method_code="POST",
        payment_method_code="cash_on_delivery",
    )
    return user, order


def test_checkout_dispatches_order_created_notification(checkout_order):
    user, order = checkout_order

    messages = NotificationMessage.objects.filter(event_name="OrderCreated")
    assert messages.count() >= 1
    assert messages.filter(channel="email", recipient=user.email).exists()
    assert Notification.objects.filter(user=user, event_name="OrderCreated").exists()

    email = [message for message in mail.outbox if "ORD" in message.subject][0]
    assert order.number in email.subject
    assert email.body.find(order.number) != -1


def test_order_paid_transition_sends_notification(checkout_order):
    user, order = checkout_order
    mail.outbox.clear()

    set_payment_status(order, Order.PAYMENT_PAID)

    messages = NotificationMessage.objects.filter(event_name="OrderPaid")
    assert messages.filter(recipient=user.email).exists()
    assert all(message.status == NotificationMessage.STATUS_SENT for message in messages)
    assert len(mail.outbox) == 1


def test_order_shipped_transition_sends_notification(checkout_order):
    user, order = checkout_order
    transition_order_status(order, Order.STATUS_PROCESSING)
    transition_order_status(order, Order.STATUS_PAID)
    mail.outbox.clear()

    from apps.orders.services import set_shipment_status

    set_shipment_status(order, Order.SHIPMENT_SHIPPED)

    assert NotificationMessage.objects.filter(event_name="OrderShipped").exists()
    assert len(mail.outbox) == 1


def test_order_cancelled_transition_sends_notification(checkout_order):
    user, order = checkout_order
    mail.outbox.clear()

    transition_order_status(order, Order.STATUS_CANCELLED)

    assert NotificationMessage.objects.filter(event_name="OrderCancelled").exists()
    assert len(mail.outbox) == 1
