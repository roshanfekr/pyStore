import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.identity.services.authentication import authenticate_credentials
from apps.orders.models import Order
from apps.orders.services import cancel_order
from apps.reviews.services import approve_review, create_review
from apps.stores.services import create_store
from core.audit.models import AuditLog
from core.audit.service import audit, mask_sensitive
from core.settings.service import settings_service

User = get_user_model()
PASSWORD = "Str0ng!Passw0rd"

pytestmark = [pytest.mark.django_db]


class FakeRequest:
    def __init__(self, user=None, ip="203.0.113.9", ua="pytest-agent"):
        self.user = user if user is not None else User.objects.none()
        self.META = {
            "REMOTE_ADDR": ip,
            "HTTP_USER_AGENT": ua,
            "HTTP_X_FORWARDED_FOR": ip,
        }


def test_audit_writes_actor_resource_and_request_data(db, sync_delivery):
    user = User.objects.create_user(email="actor@example.com", password=PASSWORD)
    request = FakeRequest(user=user)

    entry = audit(
        "test.action",
        "widget",
        "W-1",
        actor=user,
        request=request,
        before={"status": "a"},
        after={"status": "b", "password": "super-secret"},
    )

    assert entry is not None
    assert entry.actor == user
    assert entry.action == "test.action"
    assert entry.resource == "widget"
    assert entry.resource_id == "W-1"
    assert entry.ip_address == "203.0.113.9"
    assert entry.user_agent == "pytest-agent"
    assert entry.after_data["password"] == "******"
    assert entry.after_data["status"] == "b"


def test_audit_never_raises(db):
    from unittest.mock import patch

    with patch.object(AuditLog.objects, "create", side_effect=RuntimeError("db down")):
        result = audit("x", "y", "z")
    assert result is None


def test_mask_sensitive_masks_nested_secrets(db):
    data = {
        "name": "n",
        "api_key": "secret1",
        "nested": {"SECRET_TOKEN": "t", "plain": "p"},
    }
    masked = mask_sensitive(data)
    assert masked["api_key"] == "******"
    assert masked["nested"]["SECRET_TOKEN"] == "******"
    assert masked["nested"]["plain"] == "p"


def test_settings_change_is_audited(db, sync_delivery):
    from apps.notifications.settings_defs import register_notification_settings

    register_notification_settings()
    settings_service.set("notifications", "max_attempts", 3)

    entry = AuditLog.objects.filter(
        action="settings.updated", resource_id="notifications:max_attempts"
    ).latest("created_at")
    assert entry.before_data["value"] == 5
    assert entry.after_data["value"] == 3


def test_order_cancellation_is_audited(db, sync_delivery):
    store = create_store("Audit Store")

    user = User.objects.create_user(email="orderer@example.com", password=PASSWORD)
    order = Order.objects.create(store=store, user=user, email=user.email)

    before_count = AuditLog.objects.filter(action="order.status_changed").count()
    cancel_order(order, actor=user, note="audit test")
    after_count = AuditLog.objects.filter(action="order.status_changed").count()

    assert after_count == before_count + 1
    entry = AuditLog.objects.filter(action="order.status_changed").latest("created_at")
    assert entry.resource_id == order.number
    assert entry.before_data["status"] == Order.STATUS_PENDING
    assert entry.after_data["status"] == Order.STATUS_CANCELLED
    assert entry.actor == user


def test_review_moderation_is_audited(db, sync_delivery):
    from apps.catalog.services import create_product
    from apps.identity.services.roles import ensure_permission, ensure_role, grant_role

    store = create_store("Review Audit Store")
    product = create_product(store, "Audit Product", price=1)
    moderator = User.objects.create_user(email="mod@example.com", password=PASSWORD)
    permission, _ = ensure_permission("reviews.review.moderate", display_name="Moderate reviews")
    role = ensure_role("Audit Moderators")
    role.permissions.add(permission)
    grant_role(moderator, role.name)
    review = create_review(
        product, moderator, rating=4, title="T", content="Long enough review content."
    )

    approve_review(review, actor=moderator)

    entry = AuditLog.objects.filter(action="review.approved").latest("created_at")
    assert entry.resource_id == str(review.id)
    assert entry.actor == moderator
    assert entry.after_data["status"] == "approved"


def test_failed_login_is_audited(db, sync_delivery):
    User.objects.create_user(email="login-audit@example.com", password=PASSWORD)

    try:
        authenticate_credentials("login-audit@example.com", "Wrong!Pass1")
    except Exception:
        pass

    entry = AuditLog.objects.filter(action="auth.login_failed").latest("created_at")
    assert entry.actor_email == ""
    assert entry.after_data["reason"] == "invalid_credentials"


def test_successful_login_is_audited(db, sync_delivery):
    user = User.objects.create_user(email="login-ok@example.com", password=PASSWORD)
    request = FakeRequest(ip="198.51.100.7", ua="login-agent")
    authenticate_credentials("login-ok@example.com", PASSWORD, request=request)

    entry = AuditLog.objects.filter(action="auth.login").latest("created_at")
    assert entry.actor == user
    assert entry.ip_address == "198.51.100.7"
    assert entry.user_agent == "login-agent"


def test_audit_timestamp_is_utc(db):
    entry = audit("ts.check", "thing", "1")
    assert entry is not None
    assert entry.created_at.tzinfo is not None
    assert entry.created_at <= timezone.now()
