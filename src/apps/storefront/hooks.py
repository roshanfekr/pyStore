"""Rendering of plugin storefront hooks.

Both the ``plugin_hook`` Django template tag (server-rendered themes) and the
Vue storefront SPA consume the same fragments, so the rendering logic lives
here and is shared by both entry points. Plugins keep shipping plain Django
templates; the SPA receives their rendered HTML and injects it via ``v-html``.
"""

from django.template import TemplateDoesNotExist
from django.template.loader import render_to_string

from core.plugins.manager import PluginManager


def render_plugin_hook(hook_name: str, *, request=None) -> list[dict]:
    """Return ``{"plugin_id", "html"}`` fragments for every enabled plugin.

    Order follows plugin discovery order, matching the server-rendered
    template tag so themes and the SPA show hooks identically.
    """
    manager = PluginManager()
    manager.discover_plugins()

    fragments: list[dict] = []
    for plugin_id, template_name in manager.enabled_storefront_hooks(hook_name):
        try:
            plugin = manager.get_class(plugin_id)()
            extra_context = plugin.get_hook_context(hook_name) or {}
        except Exception:
            extra_context = {}
        try:
            plugin_settings = manager.get_settings(plugin_id)
        except Exception:
            plugin_settings = {}
        fragment_context = {
            "request": request,
            "plugin_id": plugin_id,
            "plugin_settings": plugin_settings,
            **extra_context,
        }
        try:
            html = render_to_string(template_name, fragment_context, request=request)
        except TemplateDoesNotExist:
            continue
        fragments.append({"plugin_id": plugin_id, "html": html})
    return fragments
