import datetime
import decimal
import json
import logging
import uuid
from typing import Any

from django.db import transaction
from django.template import Context, Template
from django.utils import timezone

from apps.notifications.exceptions import NotificationError
from apps.notifications.models import (
    Notification,
    NotificationMessage,
    NotificationTemplate,
    WebhookEndpoint,
)
from apps.notifications.settings_defs import (
    async_delivery_enabled,
    channel_enabled,
    channel_provider_setting,
    enabled_channels,
    max_attempts,
)
from core.exceptions import ValidationError
from core.notifications.registry import notification_provider_registry

logger = logging.getLogger(__name__)

DEFAULT_STORE_NAME = "our store"


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [json_safe(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (datetime.datetime, datetime.date)):
        return value.isoformat()
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, decimal.Decimal):
        return str(value)
    return str(value)


def render_context(message: NotificationMessage) -> dict:
    context = dict(message.context or {})
    context["store_name"] = message.store.name if message.store else DEFAULT_STORE_NAME
    return context


def render_template(template: NotificationTemplate, context: dict) -> tuple[str, str]:
    template_context = Context(context, autoescape=False)
    subject = Template(template.subject).render(template_context) if template.subject else ""
    body = Template(template.body).render(template_context) if template.body else ""
    return subject.strip(), body


def find_templates(
    event_name: str, channel: str, *, store=None
) -> list[NotificationTemplate]:
    templates = list(
        NotificationTemplate.objects.filter(
            event_name=event_name, channel=channel, is_active=True
        )
    )
    if store is None:
        return [template for template in templates if template.store_id is None]
    store_specific = [template for template in templates if template.store_id == store.id]
    if store_specific:
        return store_specific
    return [template for template in templates if template.store_id is None]


def resolve_recipient(channel: str, context: dict, user=None) -> str:
    if channel == NotificationTemplate.CHANNEL_EMAIL:
        return str(context.get("email") or (getattr(user, "email", "") or "")).strip()
    if channel == NotificationTemplate.CHANNEL_SMS:
        return str(context.get("phone") or "").strip()
    return ""


def resolve_provider(channel: str):

    configured_code = channel_provider_setting(channel)
    if configured_code:
        provider = notification_provider_registry.get(configured_code)
        if provider is None:
            raise NotificationError(
                f"Configured provider {configured_code!r} for channel {channel!r} is not registered"
            )
        if provider.channel != channel:
            raise NotificationError(
                f"Provider {configured_code!r} does not support channel {channel!r}"
            )
        return provider
    provider = notification_provider_registry.first_for_channel(channel)
    if provider is None:
        raise NotificationError(f"No notification provider registered for channel {channel!r}")
    return provider


def _create_messages_for_channel(
    channel: str,
    event_name: str,
    context: dict,
    *,
    store=None,
    user=None,
) -> list[NotificationMessage]:
    messages: list[NotificationMessage] = []
    if channel == NotificationTemplate.CHANNEL_WEBHOOK:
        for endpoint in WebhookEndpoint.objects.filter(is_active=True):
            if endpoint.matches_event(event_name):
                messages.append(
                    NotificationMessage.objects.create(
                        event_name=event_name,
                        channel=channel,
                        recipient=endpoint.target_url,
                        user=user,
                        store=store,
                        context=context,
                    )
                )
        return messages

    templates = find_templates(event_name, channel, store=store)
    if not templates:
        return []
    recipient = resolve_recipient(channel, context, user)
    if channel in (NotificationTemplate.CHANNEL_EMAIL, NotificationTemplate.CHANNEL_SMS) and not recipient:
        logger.info("Skipping %s notification for %s: no recipient", channel, event_name)
        return []
    if channel == NotificationTemplate.CHANNEL_INAPP and user is None:
        logger.info("Skipping in-app notification for %s: no user", event_name)
        return []

    for template in templates:
        messages.append(
            NotificationMessage.objects.create(
                event_name=event_name,
                channel=channel,
                template=template,
                recipient=recipient,
                user=user,
                store=store,
                context=context,
            )
        )
    return messages


def _schedule(message: NotificationMessage) -> None:
    if async_delivery_enabled():
        from apps.notifications.tasks import send_notification_task

        transaction.on_commit(lambda: send_notification_task.delay(str(message.pk)))
    else:
        send_message(message)


def queue_notification(
    event_name: str,
    context: dict,
    *,
    channels: list[str] | None = None,
    store=None,
    user=None,
) -> list[NotificationMessage]:
    """Create pending notification messages for an event and schedule delivery."""
    valid_channels = set(enabled_channels())
    requested = list(channels) if channels is not None else sorted(valid_channels)
    unknown = set(requested) - valid_channels
    if unknown:
        raise ValidationError(
            f"Unknown notification channels: {', '.join(sorted(unknown))}",
            code="notifications.unknown_channel",
        )
    selected = [channel for channel in requested if channel in valid_channels]
    if not selected:
        return []

    context = json_safe(context)
    context.setdefault("occurred_at", timezone.now().isoformat())
    context.setdefault("store_name", store.name if store else DEFAULT_STORE_NAME)

    messages: list[NotificationMessage] = []
    for channel in selected:
        if not channel_enabled(channel):
            continue
        try:
            messages.extend(
                _create_messages_for_channel(channel, event_name, context, store=store, user=user)
            )
        except NotificationError:
            logger.exception("No provider available for channel %s", channel)

    for message in messages:
        _schedule(message)
    return messages


def send_message(message: NotificationMessage) -> NotificationMessage:
    """Deliver one message through its channel provider (never raises)."""
    if message.status == NotificationMessage.STATUS_SENT:
        return message

    try:
        provider = resolve_provider(message.channel)
    except NotificationError as exc:
        message.status = NotificationMessage.STATUS_FAILED
        message.attempts += 1
        message.last_error = exc.message
        message.save(update_fields=["status", "attempts", "last_error"])
        logger.warning("Notification %s failed: %s", message.pk, exc.message)
        return message

    render_ctx = render_context(message)
    if message.template is not None:
        subject, body = render_template(message.template, render_ctx)
        message.subject = subject
        message.body = body
    elif not message.body and message.context:
        payload = dict(render_ctx)
        payload.pop("occurred_at", None)
        message.body = json.dumps(json_safe(payload), default=str)

    try:
        result = provider.send(message)
        message.provider_code = provider.code
        if result.successful:
            message.status = NotificationMessage.STATUS_SENT
            message.sent_at = timezone.now()
            message.last_error = ""
        else:
            message.status = NotificationMessage.STATUS_FAILED
            message.last_error = result.message
    except Exception as exc:  # provider-level failure must not break the caller
        logger.exception("Notification provider %r crashed", getattr(provider, "code", "?"))
        message.status = NotificationMessage.STATUS_FAILED
        message.last_error = str(exc)

    message.attempts += 1
    message.save(
        update_fields=[
            "subject", "body", "status", "attempts", "last_error",
            "provider_code", "sent_at",
        ]
    )
    return message


def retryable(message: NotificationMessage) -> bool:
    return message.status == NotificationMessage.STATUS_FAILED and message.attempts < max_attempts()


def send_pending_messages(limit: int = 100) -> int:
    """Recovery sweep for messages still pending (e.g. missed on_commit)."""
    sent = 0
    pending = NotificationMessage.objects.filter(
        status=NotificationMessage.STATUS_PENDING
    ).order_by("created_at")[:limit]
    for message in pending:
        send_message(message)
        sent += 1
    return sent


def user_notifications(user, *, unread_only: bool = False):
    queryset = Notification.objects.filter(user=user)
    if unread_only:
        queryset = queryset.filter(is_read=False)
    return queryset


def unread_notification_count(user) -> int:
    return Notification.objects.filter(user=user, is_read=False).count()


def mark_notification_read(notification: Notification) -> Notification:
    if not notification.is_read:
        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save(update_fields=["is_read", "read_at"])
    return notification


def mark_all_notifications_read(user) -> int:
    return Notification.objects.filter(user=user, is_read=False).update(
        is_read=True, read_at=timezone.now()
    )
