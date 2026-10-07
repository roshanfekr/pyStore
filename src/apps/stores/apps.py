from django.apps import AppConfig
from django.db.models.signals import post_delete, post_migrate, post_save
from django.dispatch import receiver


class StoresConfig(AppConfig):
    name = "apps.stores"
    label = "stores"
    verbose_name = "Stores"

    def ready(self):
        @receiver(post_save, sender="stores.LocaleStringResource")
        @receiver(post_delete, sender="stores.LocaleStringResource")
        def _translation_changed(sender, **kwargs):
            from apps.stores.services import clear_translation_cache

            clear_translation_cache()

        @receiver(post_migrate)
        def _seed_builtin_translations(sender, **kwargs):
            if sender.label != "stores":
                return
            try:
                from apps.stores.seed_translations import PERSIAN_STRINGS
                from apps.stores.services import seed_language_resources

                seed_language_resources("fa", PERSIAN_STRINGS)
            except Exception:
                pass
