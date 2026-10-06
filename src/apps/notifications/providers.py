import logging

from django.conf import settings
from django.core.mail import EmailMessage

from core.notifications.interface import NotificationProvider, NotificationSendResult
from core.notifications.registry import notification_provider_registry

logger = logging.getLogger(__name__)


class EmailNotificationProvider(NotificationProvider):
    """Sends email through the configured Django email backend."""

    code = "email_default"
    name = "Default email provider"
    channel = "email"

    def send(self, message) -> NotificationSendResult:
        recipient = (message.recipient or "").strip()
        if not recipient:
            return NotificationSendResult(successful=False, message="Missing email recipient")
        from_email = self.get_configuration().get("sender") or settings.DEFAULT_FROM_EMAIL
        email = EmailMessage(
            subject=message.subject or message.event_name,
            body=message.body or "",
            from_email=from_email,
            to=[recipient],
        )
        try:
            count = email.send(fail_silently=False)
        except Exception as exc:
            logger.warning("Email delivery to %s failed: %s", recipient, exc)
            return NotificationSendResult(successful=False, message=str(exc))
        return NotificationSendResult(successful=True, reference=f"email:{count}")


class InAppNotificationProvider(NotificationProvider):
    """Creates the in-app inbox entry for a user."""

    code = "inapp_default"
    name = "Default in-app provider"
    channel = "inapp"

    def send(self, message) -> NotificationSendResult:
        from apps.notifications.models import Notification

        if message.user_id is None:
            return NotificationSendResult(successful=False, message="In-app notifications require a user")
        notification = Notification.objects.create(
            user_id=message.user_id,
            title=message.subject or message.event_name or "Notification",
            body=message.body or "",
            level=self.get_configuration().get("level", Notification.LEVEL_INFO),
            event_name=message.event_name,
            data=message.context if isinstance(message.context, dict) else {},
        )
        return NotificationSendResult(successful=True, reference=str(notification.pk))


class WebhookNotificationProvider(NotificationProvider):
    """Delivers event payloads to registered webhook endpoints.

    Payloads are signed with HMAC-SHA256 using the endpoint secret and sent
    in the ``X-Webhook-Signature`` header. Every attempt is recorded in the
    webhook delivery log.
    """

    code = "webhook_default"
    name = "Default webhook provider"
    channel = "webhook"

    def send(self, message) -> NotificationSendResult:
        from apps.notifications.models import WebhookEndpoint
        from apps.notifications.webhooks import build_webhook_payload, deliver_webhook

        target_url = (message.recipient or "").strip()
        if not target_url:
            return NotificationSendResult(successful=False, message="Missing webhook target URL")

        endpoint = WebhookEndpoint.objects.filter(target_url=target_url, is_active=True).first()
        if endpoint is None:
            return NotificationSendResult(successful=False, message="Webhook endpoint is not registered")

        payload = build_webhook_payload(message.event_name, message.context or {})
        log = deliver_webhook(endpoint, message.event_name, payload)
        if log.successful:
            return NotificationSendResult(successful=True, reference=str(log.pk))
        return NotificationSendResult(successful=False, message=log.error or "Delivery failed")


class LoggingSMSProvider(NotificationProvider):
    """SMS abstraction that logs messages instead of calling a gateway.

    Real SMS gateways should be provided by plugins implementing
    ``NotificationProvider`` with ``channel == "sms"``.
    """

    code = "sms_logging"
    name = "Logging SMS provider"
    channel = "sms"

    def send(self, message) -> NotificationSendResult:
        logger.info("SMS to %s: %s", message.recipient, (message.body or "")[:160])
        return NotificationSendResult(successful=True, reference="sms:logged")


def register_builtin_providers() -> None:
    for provider in (
        EmailNotificationProvider(),
        InAppNotificationProvider(),
        WebhookNotificationProvider(),
        LoggingSMSProvider(),
    ):
        notification_provider_registry.register(provider)
