# Seed the product-detail storefront strings (availability, rating, share).

from django.db import migrations


def seed_storefront_strings(apps, schema_editor):
    from apps.stores.seed_translations import PERSIAN_STRINGS
    from apps.stores.services import seed_language_resources

    # Only the product-detail additions; the rest were seeded by earlier
    # migrations. Kept explicit so the migration is idempotent and scoped.
    keys = {
        key: PERSIAN_STRINGS[key]
        for key in (
            "Be the first to review this product",
            "Availability",
            "In stock",
            "Out of stock",
            "Share",
        )
        if key in PERSIAN_STRINGS
    }
    for code in ("fa",):
        seed_language_resources(code, keys)


def unseed(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("stores", "0003_seed_admin_form_labels"),
    ]

    operations = [
        migrations.RunPython(seed_storefront_strings, reverse_code=unseed),
    ]
