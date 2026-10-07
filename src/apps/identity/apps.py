from django.apps import AppConfig
from django.db.models.signals import post_migrate
from django.dispatch import receiver


class IdentityConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.identity"
    label = "identity"
    verbose_name = "Identity"


@receiver(post_migrate)
def seed_default_permissions(sender, **kwargs):
    """Seed default permissions and roles after every migrate (idempotent)."""
    if sender.label != "identity":
        return
    try:
        from apps.identity.services.roles import sync_defaults

        sync_defaults()
    except Exception:
        # Migrate must never fail because of seeding; the data migration
        # covers the first run.
        pass
