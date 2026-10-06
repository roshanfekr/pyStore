import logging

from django.apps import AppConfig
from django.db.models.signals import post_migrate

logger = logging.getLogger(__name__)


class ReviewsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.reviews"
    label = "reviews"
    verbose_name = "Reviews"

    def ready(self):
        from apps.reviews.services import register_review_settings

        register_review_settings()

        # Import for side effect: register review domain events.
        from apps.reviews import events  # noqa: F401

        post_migrate.connect(self._ensure_permissions, sender=self)

    @staticmethod
    def _ensure_permissions(sender, **kwargs):
        from apps.reviews.permissions import ensure_reviews_permissions

        try:
            ensure_reviews_permissions()
        except Exception:
            logger.exception("Failed to ensure reviews permissions")
