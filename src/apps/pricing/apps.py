from django.apps import AppConfig


class PricingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.pricing"
    label = "pricing"
    verbose_name = "Pricing"

    def ready(self):
        from apps.catalog.pricing import pricing_registry
        from apps.pricing.engine import pricing_provider

        pricing_registry.register(pricing_provider)
