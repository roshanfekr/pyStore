from pathlib import Path

from django.conf import settings

from core.plugins import theme_discovery
from core.plugins.theme_discovery import THEMES_DIR


def get_active_theme_name() -> str:
    return getattr(settings, "ACTIVE_THEME", "default")


def get_theme_dir(name: str | None = None) -> Path:
    resolved = theme_discovery.find_theme_dir(name or get_active_theme_name())
    if resolved is None:
        return THEMES_DIR / (name or get_active_theme_name())
    return resolved


def get_theme_plugin_id(name: str | None = None) -> str | None:
    """Plugin id providing the theme, if the theme comes from a plugin."""
    import json

    theme_dir = theme_discovery.find_theme_dir(name or get_active_theme_name())
    if theme_dir is None or theme_dir.parent == THEMES_DIR:
        return None
    try:
        return json.loads((theme_dir / "plugin.json").read_text(encoding="utf-8"))["id"]
    except Exception:
        return None


def list_themes() -> list[str]:
    return theme_discovery.available_theme_names()


def get_theme_manifest(name: str | None = None) -> dict:
    import json

    manifest_file = get_theme_dir(name) / "theme.json"
    if not manifest_file.exists():
        return {}
    try:
        return json.loads(manifest_file.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _plugin_theme_settings(name: str) -> dict:
    """Stored settings of the plugin providing `name`, if any."""
    plugin_id = get_theme_plugin_id(name)
    if plugin_id is None:
        return {}
    try:
        from core.plugins.models import PluginState

        state = PluginState.objects.filter(plugin_id=plugin_id).first()
    except Exception:
        return {}
    if state is None:
        return {}
    return dict(state.settings or {})


def get_theme_config(name: str | None = None) -> dict:
    manifest = get_theme_manifest(name)
    config = dict(manifest.get("config", {}))
    config.update(_plugin_theme_settings(name or get_active_theme_name()))
    return config


def get_theme_static_dir(name: str | None = None) -> Path:
    return get_theme_dir(name) / "static"
