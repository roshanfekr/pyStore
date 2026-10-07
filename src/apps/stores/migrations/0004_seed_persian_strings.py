# Generated: seed the built-in Persian word collection.

from django.db import migrations


def seed_fa_resources(apps, schema_editor):
    from apps.stores.seed_translations import PERSIAN_STRINGS
    from apps.stores.services import seed_language_resources

    seed_language_resources("fa", PERSIAN_STRINGS)


def unseed(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("stores", "0003_localestringresource"),
        ("stores", "0002_language"),
    ]

    operations = [
        migrations.RunPython(seed_fa_resources, reverse_code=unseed),
    ]
