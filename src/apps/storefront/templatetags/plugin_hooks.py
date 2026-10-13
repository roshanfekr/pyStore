from django import template
from django.utils.safestring import mark_safe

from apps.storefront.hooks import render_plugin_hook

register = template.Library()


@register.simple_tag(takes_context=True)
def plugin_hook(context, hook_name: str) -> str:
    """Render every enabled plugin partial registered for `hook_name`."""
    fragments = render_plugin_hook(hook_name, request=context.get("request"))
    return mark_safe("".join(fragment["html"] for fragment in fragments))
