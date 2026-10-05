from django.apps import AppConfig


class SamplePluginConfig(AppConfig):
    name = "plugins.sample_plugin"
    label = "sample_plugin"
    verbose_name = "Sample Plugin"
    default_auto_field = "django.db.models.BigAutoField"
