# Seed the built-in currencies (Toman as the default) plus a secondary one.

from django.db import migrations


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


def unseed_currencies(apps, schema_editor):
    Currency = apps.get_model("stores", "Currency")
    Currency.objects.filter(code__in=["IRT", "USD"]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("stores", "0005_currency_alter_store_default_currency"),
    ]

    operations = [
        migrations.RunPython(seed_currencies, reverse_code=unseed_currencies),
    ]
