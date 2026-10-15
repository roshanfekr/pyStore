# Seed the storefront cart strings (continue shopping, coupon).

from django.db import migrations


def seed_cart_strings(apps, schema_editor):
    from apps.stores.seed_translations import PERSIAN_STRINGS
    from apps.stores.services import seed_language_resources

    # Only the cart additions; the rest were seeded by earlier migrations.
    # Kept explicit so the migration is idempotent and scoped.
    keys = {
        key: PERSIAN_STRINGS[key]
        for key in (
            "Continue shopping",
            "Coupon",
        )
        if key in PERSIAN_STRINGS
    }
    for code in ("fa",):
        seed_language_resources(code, keys)


def unseed(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("stores", "0004_seed_storefront_product_strings"),
    ]

    operations = [
        migrations.RunPython(seed_cart_strings, reverse_code=unseed),
    ]
