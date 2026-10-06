from django.conf import settings
from django.db import models

from core.models import TimeStampedModel, UUIDModel


class AuditLog(UUIDModel, TimeStampedModel):
    """Immutable record of a sensitive operation.

    Stored data must already be serialized-safe and free of secrets;
    the audit service masks sensitive values before persisting.
    """

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        related_name="audit_logs",
        on_delete=models.SET_NULL,
    )
    actor_email = models.CharField(max_length=254, blank=True)
    action = models.CharField(max_length=100, db_index=True)
    resource = models.CharField(max_length=100)
    resource_id = models.CharField(max_length=100, blank=True)
    before_data = models.JSONField(null=True, blank=True)
    after_data = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=300, blank=True)

    class Meta:
        verbose_name = "Audit log"
        verbose_name_plural = "Audit logs"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.action} {self.resource}:{self.resource_id} by {self.actor_email or 'system'}"
