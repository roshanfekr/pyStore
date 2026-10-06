import uuid
from datetime import datetime
from decimal import Decimal

import pytest
from django.core import mail

from apps.notifications.exceptions import NotificationError
from apps.notifications.models import (
    Notification,
    NotificationMessage,
    NotificationTemplate,
)
from apps.notifications.services import (
    json_safe,
    mark_all_notifications_read,
    mark_notification_read,
    queue_notification,
    resolve_provider,
    send_message,
    send_pending_messages,
    unread_notification_count,
    user_notifications,
)
from core.exceptions import ValidationError

pytestmark = [pytest.mark.django_db]


def test_json_safe_converts_non_json_types():
    value = {
        "decimal": Decimal("1.5"),
        "uuid": uuid.uuid4(),
        "datetime": datetime(2026, 1, 1, 12, 0),
        "tuple": (1, 2),
        "nested": {"decimal": Decimal("2")},
    }
    import json

    assert json.loads(json.dumps(json_safe(value))) == json.loads(json.dumps(json_safe(value)))


def test_queue_notification_sends_email_and_inapp(user, sync_delivery):
    messages = queue_notification(
        "CustomerRegistered",
        {"email": user.email, "user_id": str(user.id)},
        user=user,
    )

    channels = {message.channel for message in messages}
    assert channels == {"email", "inapp"}
    assert all(message.status == NotificationMessage.STATUS_SENT for message in messages)
    assert all(message.attempts == 1 for message in messages)
    assert all(message.sent_at is not None for message in messages)
    assert len(mail.outbox) == 1
    assert Notification.objects.filter(user=user).count() == 1


def test_queue_notification_without_user_skips_inapp(sync_delivery):
    messages = queue_notification(
        "PasswordReset", {"email": "guest@example.com"}, user=None
    )
    assert {message.channel for message in messages} == {"email"}


def test_queue_notification_rejects_unknown_channel(sync_delivery):
    with pytest.raises(ValidationError):
        queue_notification("PasswordReset", {"email": "x@example.com"}, channels=["pigeon"])


def test_queue_notification_skips_disabled_channel(user, sync_delivery):
    from .conftest import set_notification_setting

    set_notification_setting("email_enabled", False)
    try:
        messages = queue_notification(
            "CustomerRegistered", {"email": user.email}, user=user
        )
        assert {message.channel for message in messages} == {"inapp"}
    finally:
        set_notification_setting("email_enabled", True)


def test_queue_notification_without_templates_creates_nothing(sync_delivery):
    NotificationTemplate.objects.all().delete()
    messages = queue_notification("PasswordReset", {"email": "x@example.com"})
    assert messages == []


def test_queue_notification_uses_store_template(store, sync_delivery):
    NotificationTemplate.objects.create(
        code="store-order-email", name="Store order", event_name="OrderCreated",
        channel=NotificationTemplate.CHANNEL_EMAIL,
        subject="[{{ store_name }}] {{ order_number }}",
        body="Store specific body",
        store=store,
    )
    messages = queue_notification(
        "OrderCreated",
        {"email": "c@example.com", "order_number": "ORD-9"},
        store=store,
    )
    email_messages = [message for message in messages if message.channel == "email"]
    assert len(email_messages) == 1
    assert email_messages[0].subject == "[Notify Store] ORD-9"
    assert len(mail.outbox) == 1
    assert mail.outbox[0].subject == "[Notify Store] ORD-9"


def test_queue_notification_webhook_endpoints(sync_delivery):
    from apps.notifications.models import WebhookEndpoint

    WebhookEndpoint.objects.create(
        target_url="https://hooks.example.com/orders", event_names=["OrderCreated"]
    )
    WebhookEndpoint.objects.create(
        target_url="https://hooks.example.com/all", event_names=["*"]
    )
    messages = queue_notification(
        "OrderCreated", {"email": "c@example.com", "order_number": "ORD-1"}
    )
    webhook_messages = [message for message in messages if message.channel == "webhook"]
    assert {message.recipient for message in webhook_messages} == {
        "https://hooks.example.com/orders",
        "https://hooks.example.com/all",
    }


def test_send_message_failure_records_error(user, sync_delivery, monkeypatch):
    from .conftest import set_notification_setting

    class CrashingProvider:
        code = "crashing"
        name = "Crashing"
        channel = "email"

        def configure(self, config):
            pass

        def get_configuration(self):
            return {}

        def supports(self, channel):
            return channel == "email"

        def send(self, message):
            raise RuntimeError("boom")

    from core.notifications.registry import notification_provider_registry

    notification_provider_registry.register(CrashingProvider())
    set_notification_setting("email_provider", "crashing")
    try:
        message = queue_notification("PasswordReset", {"email": user.email}, user=user)[0]
        assert message.status == NotificationMessage.STATUS_FAILED
        assert message.attempts == 1
        assert "boom" in message.last_error
        assert len(mail.outbox) == 0
    finally:
        set_notification_setting("email_provider", "")
        notification_provider_registry.unregister("crashing")


def test_resolve_provider_unknown_code_raises():
    from .conftest import set_notification_setting

    set_notification_setting("email_provider", "does_not_exist")
    try:
        with pytest.raises(NotificationError):
            resolve_provider("email")
    finally:
        set_notification_setting("email_provider", "")


def test_resolve_provider_wrong_channel_raises():
    from .conftest import set_notification_setting

    set_notification_setting("email_provider", "sms_logging")
    try:
        with pytest.raises(NotificationError):
            resolve_provider("email")
    finally:
        set_notification_setting("email_provider", "")


def test_send_message_is_idempotent_for_sent_messages(sync_delivery):
    message = queue_notification("PasswordReset", {"email": "x@example.com"})[0]
    assert message.status == NotificationMessage.STATUS_SENT

    again = send_message(message)
    assert again.attempts == 1
    assert len(mail.outbox) == 1


def test_send_pending_messages_sweeps_queue(sync_delivery):
    message = NotificationMessage.objects.create(
        event_name="PasswordReset",
        channel=NotificationTemplate.CHANNEL_EMAIL,
        recipient="sweep@example.com",
        context={"email": "sweep@example.com"},
    )
    sent = send_pending_messages()
    assert sent == 1
    message.refresh_from_db()
    assert message.status == NotificationMessage.STATUS_SENT


def test_inapp_read_helpers(user, sync_delivery):
    queue_notification("CustomerRegistered", {"email": user.email}, user=user)
    assert unread_notification_count(user) == 1

    notification = user_notifications(user, unread_only=True).first()
    mark_notification_read(notification)
    assert unread_notification_count(user) == 0
    assert notification.is_read is True
    assert notification.read_at is not None

    mark_notification_read(notification)
    assert unread_notification_count(user) == 0

    queue_notification("CustomerRegistered", {"email": user.email}, user=user)
    assert unread_notification_count(user) == 1
    updated = mark_all_notifications_read(user)
    assert updated == 1
    assert unread_notification_count(user) == 0
