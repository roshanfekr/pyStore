import logging

from celery import shared_task

from apps.notifications.models import NotificationMessage
from apps.notifications.services import retryable, send_message, send_pending_messages

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=8)
def send_notification_task(self, message_id: str):
    message = NotificationMessage.objects.filter(pk=message_id).first()
    if message is None or message.status == NotificationMessage.STATUS_SENT:
        return True

    send_message(message)
    if retryable(message):
        countdown = min(30 * (2 ** message.attempts), 3600)
        raise self.retry(countdown=countdown)
    return message.status == NotificationMessage.STATUS_SENT


@shared_task
def retry_failed_notifications(limit: int = 50) -> int:
    """Scheduled sweep that re-queues failed messages that may be retried."""
    retried = 0
    failed = NotificationMessage.objects.filter(
        status=NotificationMessage.STATUS_FAILED
    ).order_by("created_at")[:limit]
    for message in failed:
        if retryable(message):
            send_notification_task.delay(str(message.pk))
            retried += 1
    return retried


@shared_task
def sweep_pending_notifications(limit: int = 100) -> int:

    return send_pending_messages(limit=limit)


@shared_task
def retry_webhook_delivery_task(endpoint_id: str, event_name: str, payload: dict, attempt: int = 1) -> bool:
    from apps.notifications.webhooks import deliver_webhook_with_retry

    return deliver_webhook_with_retry(endpoint_id, event_name, payload, attempt=attempt)
