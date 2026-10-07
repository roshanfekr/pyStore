from django import template
from django.utils import translation

from apps.stores.services import lookup_translation

register = template.Library()


@register.simple_tag
def tr(key: str, **format_kwargs) -> str:
    """Translate `key` for the active language via the DB word collection."""
    return lookup_translation(translation.get_language() or "en", key, **format_kwargs)
