from django import template
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe

from core.plugins.manager import PluginManager

register = template.Library()


@register.simple_tag(takes_context=True)
def plugin_hook(context, hook_name: str) -> str:
    """Render every enabled plugin partial registered for `hook_name`."""
    request = context.get("request")
    manager = PluginManager()
    manager.discover_plugins()

    fragments: list[str] = []
    for plugin_id, template_name in manager.enabled_storefront_hooks(hook_name):
        try:
            plugin = manager.get_class(plugin_id)()
            extra_context = plugin.get_hook_context(hook_name) or {}
        except Exception:
            extra_context = {}
        try:
            settings = manager.get_settings(plugin_id)
        except Exception:
            settings = {}
        fragment_context = {
            "request": request,
            "plugin_id": plugin_id,
            "plugin_settings": settings,
            **extra_context,
        }
        try:
            fragments.append(render_to_string(template_name, fragment_context, request=request))
        except template.TemplateDoesNotExist:
            continue
    return mark_safe("".join(fragments))
