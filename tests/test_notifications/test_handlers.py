import pytest
from django.core import mail

from apps.identity.events import CustomerRegistered, PasswordReset
from apps.notifications.models import Notification, NotificationMessage, WebhookEndpoint
from apps.orders.events import OrderCancelled, OrderCreated, OrderPaid, OrderShipped
from core.events import dispatcher

pytestmark = [pytest.mark.django_db]


@pytest.fixture
def sync_delivery(db):
    from core.settings.service import settings_service

    settings_service.set("notifications", "async_delivery", False)
    yield
    settings_service.set("notifications", "async_delivery", True)


def dispatch(event):
    dispatcher.dispatch(event)


def test_customer_registered_triggers_email_and_inapp(user, sync_delivery):
    dispatch(CustomerRegistered(email=user.email, user_id=str(user.id)))

    assert NotificationMessage.objects.filter(event_name="CustomerRegistered", channel="email").exists()
    assert Notification.objects.filter(user=user, event_name="CustomerRegistered").exists()
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [user.email]


def test_customer_registered_guest_skips_inapp(sync_delivery):
    dispatch(CustomerRegistered(email="guest@example.com", user_id=""))
    assert NotificationMessage.objects.filter(
        event_name="CustomerRegistered", channel="inapp"
    ).exists() is False
    assert len(mail.outbox) == 1


def test_password_reset_triggers_email(sync_delivery):
    dispatch(PasswordReset(email="reset@example.com"))
    assert len(mail.outbox) == 1
    assert "password" in mail.outbox[0].subject.lower()


def test_order_events_trigger_notifications(sync_delivery):
    order_context = {
        "order_id": "11111111-1111-1111-1111-111111111111",
        "order_number": "ORD-NOTIF-1",
        "email": "buyer@example.com",
        "user_id": "",
        "total": "120.0000",
        "currency": "USD",
    }
    dispatch(OrderCreated(**order_context))
    dispatch(OrderPaid(**order_context))
    dispatch(OrderShipped(**order_context))
    dispatch(OrderCancelled(**order_context))

    assert NotificationMessage.objects.filter(event_name="OrderCreated", channel="email").exists()
    assert NotificationMessage.objects.filter(event_name="OrderPaid", channel="email").exists()
    assert NotificationMessage.objects.filter(event_name="OrderShipped", channel="email").exists()
    assert NotificationMessage.objects.filter(event_name="OrderCancelled", channel="email").exists()
    assert len(mail.outbox) == 4
    subjects = [message.subject for message in mail.outbox]
    assert any("ORD-NOTIF-1" in subject for subject in subjects)


def test_order_paid_reaches_webhook_endpoint(sync_delivery, monkeypatch):
    class FakeResponse:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    captured = []
    monkeypatch.setattr(
        "apps.notifications.webhooks.urllib.request.urlopen",
        lambda request, timeout=10: (captured.append(request), FakeResponse())[1],
    )
    WebhookEndpoint.objects.create(
        target_url="https://hooks.example.com/paid",
        event_names=["OrderPaid"],
        secret="whsec",
    )

    dispatch(OrderPaid(order_number="ORD-WH-1", email="buyer@example.com", total="5", currency="USD"))

    webhook_messages = NotificationMessage.objects.filter(
        event_name="OrderPaid", channel="webhook"
    )
    assert webhook_messages.count() == 1
    assert webhook_messages.first().status == NotificationMessage.STATUS_SENT
    assert len(captured) == 1


def test_handler_failure_does_not_break_dispatch(sync_delivery):
    from apps.notifications.services import queue_notification

    def broken(event):
        raise RuntimeError("handler bug")

    from core.events import register_handler

    register_handler(PasswordReset, broken)
    try:
        dispatch(PasswordReset(email="still-sent@example.com"))
    finally:
        dispatcher.unsubscribe(PasswordReset, broken)

    assert len(mail.outbox) == 1
    assert queue_notification is not None
