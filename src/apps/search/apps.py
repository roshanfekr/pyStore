from django.apps import AppConfig


class SearchConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.search"
    label = "search"
    verbose_name = "Search"

    def ready(self):
        from .signals import connect_signals

        connect_signals()
