# Generated: seed default permissions and default role assignments.

from django.db import migrations


def seed_defaults(apps, schema_editor):
    from apps.identity.services.roles import sync_defaults

    sync_defaults()


def unseed_defaults(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("identity", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_defaults, reverse_code=unseed_defaults),
    ]
