from django.core.management.base import BaseCommand

from apps.stores.seed_translations import PERSIAN_STRINGS
from apps.stores.services import collect_template_strings, seed_language_resources


class Command(BaseCommand):
    help = "Collect {% tr %} strings from templates and seed built-in word collections."

    def handle(self, *args, **options):
        keys = collect_template_strings()
        self.stdout.write(f"Collected {len(keys)} template string(s).")

        created = seed_language_resources("fa", PERSIAN_STRINGS)
        self.stdout.write(f"Seeded {created} new Persian entr(ies).")
