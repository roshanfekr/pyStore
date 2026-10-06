from django.apps import AppConfig


class OrdersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.orders"
    label = "orders"
    verbose_name = "Orders"

    def ready(self):
        # Import for side effect: register order domain events with the
        # event registry so async dispatch can rebuild them from payloads.
        from apps.orders import events  # noqa: F401
