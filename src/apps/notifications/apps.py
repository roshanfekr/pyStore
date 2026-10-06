import logging

from django.apps import AppConfig
from django.db.models.signals import post_migrate

logger = logging.getLogger(__name__)


class NotificationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.notifications"
    label = "notifications"
    verbose_name = "Notifications"

    def ready(self):
        from apps.notifications.providers import register_builtin_providers
        from apps.notifications.settings_defs import register_notification_settings

        register_builtin_providers()
        register_notification_settings()

        post_migrate.connect(self._seed_default_templates, sender=self)

        self._register_event_handlers()

    @staticmethod
    def _seed_default_templates(sender, **kwargs):
        from apps.notifications.templates_defaults import (
            ensure_default_notification_templates,
        )

        try:
            ensure_default_notification_templates()
        except Exception:
            logger.exception("Failed to seed default notification templates")

    @staticmethod
    def _register_event_handlers():
        from apps.identity.events import CustomerRegistered, PasswordReset
        from apps.notifications import handlers
        from apps.orders.events import OrderCancelled, OrderCreated, OrderPaid, OrderShipped
        from core.events import register_handler

        register_handler(CustomerRegistered, handlers.handle_customer_registered)
        register_handler(PasswordReset, handlers.handle_password_reset)
        register_handler(OrderCreated, handlers.handle_order_created)
        register_handler(OrderPaid, handlers.handle_order_paid)
        register_handler(OrderShipped, handlers.handle_order_shipped)
        register_handler(OrderCancelled, handlers.handle_order_cancelled)
