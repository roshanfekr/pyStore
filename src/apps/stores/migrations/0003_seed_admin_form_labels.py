# Seed the namespaced product-definition form labels (admin.form.* keys).
#
# These keys are unique (``admin.form.<app_label>.<model>.<field>``) so the
# admin labels never collide with the storefront word collection, which is
# matched case-insensitively on the English source string.

from django.db import migrations


def seed_admin_labels(apps, schema_editor):
    from apps.stores.seed_translations import PERSIAN_STRINGS
    from apps.stores.services import seed_language_resources

    # Only the namespaced admin keys; the rest were seeded by migration 0002
    # (or later additions are picked up by the ``seed_translations`` command).
    admin_keys = {
        key: value
        for key, value in PERSIAN_STRINGS.items()
        if key.startswith(("admin.form.", "admin.inline.", "admin.image."))
    }
    for code in ("fa",):
        seed_language_resources(code, admin_keys)


def unseed(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("stores", "0002_seed_languages_currencies"),
    ]

    operations = [
        migrations.RunPython(seed_admin_labels, reverse_code=unseed),
    ]
