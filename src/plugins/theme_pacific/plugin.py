from core.plugins import theme_discovery
from core.plugins.base import Plugin
from core.plugins.exceptions import PluginError
from plugins.theme_pacific.settings import DEFAULTS

THEME_SLUG = "pacific"


class PacificThemePlugin(Plugin):
    def on_install(self):
        theme_dir = theme_discovery.discover_plugin_themes().get(THEME_SLUG)
        if theme_dir is None:
            raise PluginError("Pacific theme assets are missing the theme.json manifest")
        if not (theme_dir / "templates" / "storefront" / "base.html").exists():
            raise PluginError("Pacific theme assets are missing storefront templates")

    def get_settings_defaults(self):
        return dict(DEFAULTS)

    def get_settings_schema(self):
        return {
            "announcement_text": {"label": "Announcement bar text", "type": "string"},
            "hero_title": {"label": "Hero title", "type": "string"},
            "hero_subtitle": {"label": "Hero subtitle", "type": "text"},
            "footer_about": {"label": "Footer about text", "type": "text"},
            "primary_color": {"label": "Primary color (hex)", "type": "string"},
            "accent_color": {"label": "Accent color (hex)", "type": "string"},
        }
