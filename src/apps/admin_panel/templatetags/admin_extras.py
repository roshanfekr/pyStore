from django import template

from apps.admin_panel.i18n import translate_text

register = template.Library()


@register.filter
def get_item(mapping, key):
    return mapping.get(key)


@register.simple_tag
def admin_tr(key: str, default: str) -> str:
    """Translate a namespaced admin key, falling back to ``default``."""
    return translate_text(key, default)
