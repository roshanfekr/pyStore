import pytest
from django.core import mail

from apps.notifications.models import NotificationMessage
from apps.notifications.services import queue_notification, retryable
from apps.notifications.tasks import (
    retry_failed_notifications,
    send_notification_task,
    sweep_pending_notifications,
)
from core.settings.service import settings_service

pytestmark = [pytest.mark.django_db]


@pytest.fixture
def sync_delivery(db):
    settings_service.set("notifications", "async_delivery", False)
    yield
    settings_service.set("notifications", "async_delivery", True)


def test_send_notification_task_via_on_commit(django_capture_on_commit_callbacks, db):
    from .conftest import set_notification_setting

    set_notification_setting("async_delivery", True)
    with django_capture_on_commit_callbacks(execute=True):
        message = queue_notification("PasswordReset", {"email": "task@example.com"})[0]
        message_id = str(message.pk)
    message.refresh_from_db()
    assert message.status == NotificationMessage.STATUS_SENT
    assert mail.outbox[0].to == ["task@example.com"]
    assert message_id


def test_send_notification_task_ignores_missing_or_sent(sync_delivery):
    assert send_notification_task.delay("00000000-0000-0000-0000-000000000000").get() is True

    message = NotificationMessage.objects.create(
        event_name="X", channel="email", recipient="a@b.com",
        status=NotificationMessage.STATUS_SENT,
    )
    assert send_notification_task.delay(str(message.pk)).get() is True


def test_retryable_logic(sync_delivery):
    message = NotificationMessage.objects.create(
        event_name="X", channel="email", recipient="a@b.com",
        status=NotificationMessage.STATUS_FAILED, attempts=1,
    )
    assert retryable(message) is True

    message.attempts = 5
    assert retryable(message) is False

    message.status = NotificationMessage.STATUS_SENT
    assert retryable(message) is False


def test_retry_failed_notifications_sweeps_failed(sync_delivery):
    message = NotificationMessage.objects.create(
        event_name="PasswordReset", channel="email", recipient="retry@example.com",
        status=NotificationMessage.STATUS_FAILED, attempts=1,
        context={"email": "retry@example.com"},
    )
    result = retry_failed_notifications.delay().get()
    assert result == 1
    message.refresh_from_db()
    assert message.attempts == 2
    assert message.status == NotificationMessage.STATUS_SENT


def test_sweep_pending_notifications(sync_delivery):
    NotificationMessage.objects.create(
        event_name="PasswordReset", channel="email", recipient="sweep2@example.com",
        context={"email": "sweep2@example.com"},
    )
    swept = sweep_pending_notifications.delay().get()
    assert swept == 1
