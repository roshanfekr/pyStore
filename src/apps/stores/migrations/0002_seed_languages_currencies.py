# Seed the built-in languages, currencies and Persian word collection.

from django.db import migrations


def seed_languages(apps, schema_editor):
    Language = apps.get_model("stores", "Language")
    Language.objects.get_or_create(
        code="en",
        defaults={"name": "English", "is_active": True, "is_default": True, "ordering": 0},
    )
    Language.objects.get_or_create(
        code="fa",
        defaults={
            "name": "فارسی",
            "is_active": True,
            "direction": "rtl",
            "flag": "🇮🇷",
            "ordering": 1,
        },
    )


def seed_currencies(apps, schema_editor):
    Currency = apps.get_model("stores", "Currency")
    Currency.objects.get_or_create(
        code="IRT",
        defaults={
            "name": "Iranian Toman",
            "symbol": "تومان",
            "decimal_places": 0,
            "is_active": True,
            "is_default": True,
            "ordering": 0,
        },
    )
    Currency.objects.get_or_create(
        code="USD",
        defaults={
            "name": "US Dollar",
            "symbol": "$",
            "decimal_places": 2,
            "is_active": True,
            "is_default": False,
            "ordering": 1,
        },
    )


def seed_persian_strings(apps, schema_editor):
    from apps.stores.seed_translations import PERSIAN_STRINGS
    from apps.stores.services import seed_language_resources

    seed_language_resources("fa", PERSIAN_STRINGS)


def unseed(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("stores", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_languages, reverse_code=unseed),
        migrations.RunPython(seed_currencies, reverse_code=unseed),
        migrations.RunPython(seed_persian_strings, reverse_code=unseed),
    ]
