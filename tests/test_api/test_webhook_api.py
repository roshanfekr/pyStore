import hashlib
import hmac
import json

import pytest
from rest_framework.test import APIClient

from apps.notifications.models import WebhookDeliveryLog, WebhookEndpoint

pytestmark = [pytest.mark.django_db]


class FakeResponse:
    def __init__(self, status):
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def endpoint(**overrides):
    defaults = {
        "target_url": "https://hooks.example.com/api",
        "secret": "whsec_super_secret_123",
        "event_names": ["OrderPaid"],
    }
    defaults.update(overrides)
    return WebhookEndpoint.objects.create(**defaults)


def test_webhook_endpoint_crud_requires_staff(api_client, db):
    response = api_client.post(
        "/api/v1/webhooks/endpoints",
        {"target_url": "https://hooks.example.com/x", "event_names": ["OrderPaid"]},
        format="json",
    )
    assert response.status_code == 401

    from django.contrib.auth import get_user_model

    User = get_user_model()
    user = User.objects.create_user(email="plain@example.com", password="Str0ng!Passw0rd")
    client = APIClient()
    client.force_authenticate(user=user)
    assert client.get("/api/v1/webhooks/endpoints").status_code == 403

    user.is_staff = True
    user.save()
    response = client.get("/api/v1/webhooks/endpoints")
    assert response.status_code == 200


def test_webhook_endpoint_create_and_validate(api_client, db):
    from django.contrib.auth import get_user_model

    User = get_user_model()
    user = User.objects.create_user(email="adminwh@example.com", password="Str0ng!Passw0rd", is_staff=True)
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.post(
        "/api/v1/webhooks/endpoints",
        {"target_url": "https://hooks.example.com/new", "event_names": ["OrderPaid", "*"]},
        format="json",
    )
    assert response.status_code == 201
    assert response.data["max_retries"] == 3

    response = client.post(
        "/api/v1/webhooks/endpoints",
        {"target_url": "https://hooks.example.com/bad", "event_names": "OrderPaid"},
        format="json",
    )
    assert response.status_code == 400

    response = client.post(
        "/api/v1/webhooks/endpoints",
        {"target_url": "https://hooks.example.com/bad", "event_names": ["X"], "secret": "short"},
        format="json",
    )
    assert response.status_code == 400


def test_webhook_endpoint_event_filter(api_client, db):
    from django.contrib.auth import get_user_model

    User = get_user_model()
    user = User.objects.create_user(email="filterwh@example.com", password="Str0ng!Passw0rd", is_staff=True)
    client = APIClient()
    client.force_authenticate(user=user)

    endpoint(event_names=["OrderPaid"])
    endpoint(target_url="https://hooks.example.com/all", event_names=["*"])

    response = client.get("/api/v1/webhooks/endpoints", {"event": "OrderPaid"})
    assert response.data["count"] == 2

    response = client.get("/api/v1/webhooks/endpoints", {"event": "OrderCreated"})
    assert response.data["count"] == 1


def test_delivery_log_records_attempts(db, monkeypatch):
    target = endpoint()
    monkeypatch.setattr(
        "apps.notifications.webhooks.urllib.request.urlopen",
        lambda request, timeout=10: FakeResponse(500),
    )
    from apps.notifications.webhooks import deliver_webhook

    payload = {"event_name": "OrderPaid", "context": {}}
    log = deliver_webhook(target, "OrderPaid", payload, attempt=1)
    assert log.successful is False
    assert log.status_code == 500

    monkeypatch.setattr(
        "apps.notifications.webhooks.urllib.request.urlopen",
        lambda request, timeout=10: FakeResponse(200),
    )
    log = deliver_webhook(target, "OrderPaid", payload, attempt=2)
    assert log.successful is True

    assert WebhookDeliveryLog.objects.filter(endpoint=target).count() == 2


def test_delivery_with_retry_schedules_task(db, monkeypatch):
    scheduled = []

    def fake_apply_async(*args, **kwargs):
        scheduled.append(kwargs)
        return None

    target = endpoint(max_retries=2)
    monkeypatch.setattr(
        "apps.notifications.webhooks.urllib.request.urlopen",
        lambda request, timeout=10: FakeResponse(500),
    )
    monkeypatch.setattr(
        "apps.notifications.tasks.retry_webhook_delivery_task.apply_async",
        fake_apply_async,
    )

    from apps.notifications.webhooks import deliver_webhook_with_retry

    result = deliver_webhook_with_retry(str(target.pk), "OrderPaid", {"context": {}}, attempt=1)
    assert result is False
    assert len(scheduled) == 1
    assert scheduled[0]["args"][3] == 2

    result = deliver_webhook_with_retry(str(target.pk), "OrderPaid", {"context": {}}, attempt=3)
    assert result is False
    assert len(scheduled) == 1


def test_delivery_log_api_lists_attempts(api_client, db):
    target = endpoint()
    WebhookDeliveryLog.objects.create(
        endpoint=target, event_name="OrderPaid", attempt=1, successful=True, status_code=200
    )

    from django.contrib.auth import get_user_model

    User = get_user_model()
    user = User.objects.create_user(email="logview@example.com", password="Str0ng!Passw0rd", is_staff=True)
    client = APIClient()
    client.force_authenticate(user=user)
    response = client.get("/api/v1/webhooks/delivery-logs")
    assert response.status_code == 200
    assert response.data["count"] == 1
    assert response.data["results"][0]["successful"] is True


def test_signed_webhook_payload_verification(db, monkeypatch):
    captured = {}

    def fake_urlopen(request, timeout=10):
        captured["request"] = request
        return FakeResponse(200)

    target = endpoint()
    monkeypatch.setattr(
        "apps.notifications.webhooks.urllib.request.urlopen", fake_urlopen
    )
    from apps.notifications.webhooks import build_webhook_payload, deliver_webhook

    payload = build_webhook_payload("OrderPaid", {"order_number": "ORD-1"})
    deliver_webhook(target, "OrderPaid", payload)

    request = captured["request"]
    headers = {key.lower(): value for key, value in request.header_items()}
    expected = hmac.new(b"whsec_super_secret_123", request.data, hashlib.sha256).hexdigest()
    assert headers["x-webhook-signature"] == expected
    assert json.loads(request.data)["context"]["order_number"] == "ORD-1"
