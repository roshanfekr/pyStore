from django.conf import settings
from django.db import models

from core.models import BaseModel, TimeStampedModel


class NotificationTemplate(BaseModel):
    """Configurable Django-template content used to render notifications.

    Templates are plain-text Django templates rendered with the event
    context (plus ``store_name`` and ``occurred_at``). Store-specific
    templates override global ones for the same event/channel.
    """

    CHANNEL_EMAIL = "email"
    CHANNEL_INAPP = "inapp"
    CHANNEL_WEBHOOK = "webhook"
    CHANNEL_SMS = "sms"
    CHANNEL_CHOICES = [
        (CHANNEL_EMAIL, "Email"),
        (CHANNEL_INAPP, "In-app"),
        (CHANNEL_WEBHOOK, "Webhook"),
        (CHANNEL_SMS, "SMS"),
    ]

    code = models.SlugField(max_length=100, unique=True)
    name = models.CharField(max_length=200)
    event_name = models.CharField(max_length=100, db_index=True)
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES, db_index=True)
    subject = models.CharField(max_length=255, blank=True)
    body = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    store = models.ForeignKey(
        "stores.Store",
        null=True,
        blank=True,
        related_name="notification_templates",
        on_delete=models.CASCADE,
    )

    class Meta:
        verbose_name = "Notification template"
        verbose_name_plural = "Notification templates"
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} ({self.channel})"


class WebhookEndpoint(BaseModel):
    """Outbound webhook endpoint used by the webhook notification channel."""

    target_url = models.URLField(max_length=500, unique=True)
    secret = models.CharField(max_length=128, blank=True)
    event_names = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)
    max_retries = models.PositiveIntegerField(default=3)
    description = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = "Webhook endpoint"
        verbose_name_plural = "Webhook endpoints"
        ordering = ["target_url"]

    def __str__(self):
        return self.target_url

    def matches_event(self, event_name: str) -> bool:
        names = self.event_names or []
        return "*" in names or event_name in names


class WebhookDeliveryLog(TimeStampedModel):
    """Audit record of one webhook delivery attempt."""

    endpoint = models.ForeignKey(
        WebhookEndpoint, related_name="delivery_logs", on_delete=models.CASCADE
    )
    event_name = models.CharField(max_length=100, db_index=True)
    attempt = models.PositiveIntegerField(default=1)
    successful = models.BooleanField(default=False)
    status_code = models.PositiveIntegerField(null=True, blank=True)
    error = models.TextField(blank=True)
    duration_ms = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Webhook delivery log"
        verbose_name_plural = "Webhook delivery logs"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.event_name} -> {self.endpoint_id} (#{self.attempt})"


class NotificationMessage(BaseModel):
    """Delivery record for one notification through one channel."""

    STATUS_PENDING = "pending"
    STATUS_SENT = "sent"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_SENT, "Sent"),
        (STATUS_FAILED, "Failed"),
    ]

    event_name = models.CharField(max_length=100, blank=True, db_index=True)
    channel = models.CharField(max_length=20, choices=NotificationTemplate.CHANNEL_CHOICES, db_index=True)
    template = models.ForeignKey(
        NotificationTemplate,
        null=True,
        blank=True,
        related_name="messages",
        on_delete=models.SET_NULL,
    )
    provider_code = models.CharField(max_length=100, blank=True)
    recipient = models.CharField(max_length=254, blank=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        related_name="notification_messages",
        on_delete=models.SET_NULL,
    )
    store = models.ForeignKey(
        "stores.Store",
        null=True,
        blank=True,
        related_name="notification_messages",
        on_delete=models.SET_NULL,
    )
    subject = models.CharField(max_length=255, blank=True)
    body = models.TextField(blank=True)
    context = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True)
    attempts = models.PositiveIntegerField(default=0)
    last_error = models.TextField(blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Notification message"
        verbose_name_plural = "Notification messages"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.event_name or 'notification'} -> {self.channel}:{self.recipient}"


class Notification(BaseModel):
    """In-app notification shown in the customer/staff inbox."""

    LEVEL_INFO = "info"
    LEVEL_SUCCESS = "success"
    LEVEL_WARNING = "warning"
    LEVEL_ERROR = "error"
    LEVEL_CHOICES = [
        (LEVEL_INFO, "Info"),
        (LEVEL_SUCCESS, "Success"),
        (LEVEL_WARNING, "Warning"),
        (LEVEL_ERROR, "Error"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name="notifications", on_delete=models.CASCADE
    )
    title = models.CharField(max_length=255)
    body = models.TextField(blank=True)
    level = models.CharField(max_length=10, choices=LEVEL_CHOICES, default=LEVEL_INFO)
    event_name = models.CharField(max_length=100, blank=True, db_index=True)
    data = models.JSONField(default=dict, blank=True)
    is_read = models.BooleanField(default=False, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} ({self.user_id})"
