from django.apps import AppConfig


class AjaxCartPluginConfig(AppConfig):
    name = "plugins.ajax_cart"
    label = "ajax_cart"
    verbose_name = "AjaxCart"
    default_auto_field = "django.db.models.BigAutoField"
