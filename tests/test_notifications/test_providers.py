import hashlib
import hmac
import json

import pytest
from django.core import mail

from apps.notifications.models import (
    Notification,
    NotificationMessage,
    WebhookDeliveryLog,
    WebhookEndpoint,
)
from apps.notifications.providers import (
    EmailNotificationProvider,
    InAppNotificationProvider,
    LoggingSMSProvider,
    WebhookNotificationProvider,
    register_builtin_providers,
)
from core.notifications.registry import notification_provider_registry

pytestmark = [pytest.mark.django_db]


def make_message(**kwargs):
    defaults = {
        "event_name": "OrderCreated",
        "channel": "email",
        "recipient": "buyer@example.com",
        "subject": "Order ORD-1",
        "body": "Your order",
        "context": {"order_number": "ORD-1"},
    }
    defaults.update(kwargs)
    return NotificationMessage.objects.create(**defaults)


class FakeResponse:
    def __init__(self, status):
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def test_email_provider_sends_via_django_backend():
    result = EmailNotificationProvider().send(make_message())

    assert result.successful is True
    assert len(mail.outbox) == 1
    assert mail.outbox[0].subject == "Order ORD-1"
    assert mail.outbox[0].to == ["buyer@example.com"]


def test_email_provider_requires_recipient():
    result = EmailNotificationProvider().send(make_message(recipient=""))
    assert result.successful is False
    assert len(mail.outbox) == 0


def test_email_provider_uses_configured_sender():
    provider = EmailNotificationProvider()
    provider.configure({"sender": "shop@example.com"})
    provider.send(make_message())
    assert mail.outbox[0].from_email == "shop@example.com"


def test_inapp_provider_creates_notification(user):
    message = make_message(channel="inapp", user=user, recipient="")
    result = InAppNotificationProvider().send(message)

    assert result.successful is True
    notification = Notification.objects.get(pk=result.reference)
    assert notification.user == user
    assert notification.title == "Order ORD-1"
    assert notification.event_name == "OrderCreated"
    assert notification.data == {"order_number": "ORD-1"}


def test_inapp_provider_requires_user():
    result = InAppNotificationProvider().send(make_message(channel="inapp", user=None))
    assert result.successful is False


def test_webhook_provider_signs_payload(monkeypatch):
    endpoint = WebhookEndpoint.objects.create(
        target_url="https://hooks.example.com/x",
        secret="topsecret",
        event_names=["OrderCreated"],
    )
    captured = {}

    def fake_urlopen(request, timeout=10):
        captured["request"] = request
        return FakeResponse(200)

    monkeypatch.setattr("apps.notifications.webhooks.urllib.request.urlopen", fake_urlopen)

    message = make_message(channel="webhook", recipient=endpoint.target_url)
    result = WebhookNotificationProvider().send(message)

    assert result.successful is True
    request = captured["request"]
    headers = {key.lower(): value for key, value in request.header_items()}
    expected = hmac.new(b"topsecret", request.data, hashlib.sha256).hexdigest()
    assert headers["x-webhook-signature"] == expected
    assert headers["x-webhook-event"] == "OrderCreated"
    payload = json.loads(request.data)
    assert payload["event_name"] == "OrderCreated"
    assert payload["context"]["order_number"] == "ORD-1"
    assert WebhookDeliveryLog.objects.filter(endpoint=endpoint).count() == 1


def test_webhook_provider_rejects_non_2xx(monkeypatch):
    endpoint = WebhookEndpoint.objects.create(
        target_url="https://hooks.example.com/fail", event_names=["*"]
    )
    monkeypatch.setattr(
        "apps.notifications.webhooks.urllib.request.urlopen",
        lambda request, timeout=10: FakeResponse(500),
    )
    message = make_message(channel="webhook", recipient=endpoint.target_url)
    result = WebhookNotificationProvider().send(message)
    assert result.successful is False
    assert "500" in result.message


def test_webhook_provider_requires_registered_endpoint():
    message = make_message(channel="webhook", recipient="https://unknown.example.com/x")
    result = WebhookNotificationProvider().send(message)
    assert result.successful is False


def test_sms_provider_logs_message(caplog):
    message = make_message(channel="sms", recipient="+989121234567", body="Hello SMS")
    with caplog.at_level("INFO", logger="apps.notifications.providers"):
        result = LoggingSMSProvider().send(message)
    assert result.successful is True
    assert any("Hello SMS" in record.message for record in caplog.records)


def test_builtin_providers_registered():
    notification_provider_registry.unregister("email_default")
    notification_provider_registry.unregister("inapp_default")
    notification_provider_registry.unregister("webhook_default")
    notification_provider_registry.unregister("sms_logging")

    register_builtin_providers()

    assert notification_provider_registry.first_for_channel("email") is not None
    assert notification_provider_registry.first_for_channel("inapp") is not None
    assert notification_provider_registry.first_for_channel("webhook") is not None
    assert notification_provider_registry.first_for_channel("sms") is not None


def test_registry_requires_code_and_channel():
    from core.notifications.registry import NotificationProviderRegistry

    class Bare:
        code = ""
        channel = ""

    registry = NotificationProviderRegistry()
    with pytest.raises(ValueError):
        registry.register(Bare())
