import pytest

from apps.notifications.models import (
    Notification,
    NotificationMessage,
    NotificationTemplate,
    WebhookEndpoint,
)
from apps.notifications.services import find_templates, render_template

pytestmark = [pytest.mark.django_db]


def test_template_str_and_defaults(store):
    template = NotificationTemplate.objects.create(
        code="t1", name="T1", event_name="X", channel=NotificationTemplate.CHANNEL_EMAIL
    )
    assert str(template) == "t1 (email)"
    assert template.is_active is True
    assert template.store_id is None


def test_message_str_and_default_status():
    message = NotificationMessage.objects.create(
        event_name="OrderCreated", channel=NotificationTemplate.CHANNEL_EMAIL, recipient="a@b.com"
    )
    assert message.status == NotificationMessage.STATUS_PENDING
    assert message.attempts == 0
    assert "OrderCreated" in str(message)


def test_notification_str_and_defaults(user):
    notification = Notification.objects.create(user=user, title="Hello")
    assert notification.level == Notification.LEVEL_INFO
    assert notification.is_read is False
    assert notification.read_at is None
    assert "Hello" in str(notification)


def test_webhook_endpoint_matches_event():
    endpoint = WebhookEndpoint.objects.create(
        target_url="https://hooks.example.com/a", event_names=["OrderPaid"]
    )
    assert endpoint.matches_event("OrderPaid") is True
    assert endpoint.matches_event("OrderCreated") is False

    catch_all = WebhookEndpoint.objects.create(
        target_url="https://hooks.example.com/b", event_names=["*"]
    )
    assert catch_all.matches_event("Anything") is True


def test_find_templates_prefers_store_specific(store):
    NotificationTemplate.objects.create(
        code="global-t", name="G", event_name="OrderCreated",
        channel=NotificationTemplate.CHANNEL_EMAIL, subject="global",
    )
    store_template = NotificationTemplate.objects.create(
        code="store-t", name="S", event_name="OrderCreated",
        channel=NotificationTemplate.CHANNEL_EMAIL, subject="store", store=store,
    )

    found = find_templates("OrderCreated", NotificationTemplate.CHANNEL_EMAIL, store=store)
    assert [template.code for template in found] == [store_template.code]

    found_global = find_templates("OrderCreated", NotificationTemplate.CHANNEL_EMAIL)
    assert found_global[0].code == "global-t"

    assert find_templates("Unknown", NotificationTemplate.CHANNEL_EMAIL) == []


def test_render_template_substitutes_context():
    template = NotificationTemplate.objects.create(
        code="render-t", name="R", event_name="OrderCreated",
        channel=NotificationTemplate.CHANNEL_EMAIL,
        subject="Order {{ order_number }}",
        body="Hello {{ customer }}, total {{ total }} {{ currency }} from {{ store_name }}",
    )
    subject, body = render_template(
        template,
        {"order_number": "ORD-1", "customer": "Ali", "total": "10", "currency": "USD", "store_name": "Shop"},
    )
    assert subject == "Order ORD-1"
    assert body == "Hello Ali, total 10 USD from Shop"


def test_inactive_templates_are_ignored():
    NotificationTemplate.objects.create(
        code="inactive-t", name="I", event_name="OnlyInactive",
        channel=NotificationTemplate.CHANNEL_EMAIL, is_active=False,
    )
    assert find_templates("OnlyInactive", NotificationTemplate.CHANNEL_EMAIL) == []
