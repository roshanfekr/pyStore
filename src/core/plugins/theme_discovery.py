"""Discovery of storefront themes shipped by plugins.

In nopCommerce every theme ships as a plugin package (manifest + views +
content). pyStore follows the same pattern: a plugin directory under
``src/plugins/`` may contain a ``theme.json`` manifest together with
``templates/`` and ``static/`` assets. The theme slug is the plugin directory
name without the ``theme_`` prefix, e.g. ``plugins/theme_pacific`` provides
the ``pacific`` theme.

Built-in themes in ``src/themes/<slug>/`` always take precedence over
plugin themes with the same slug.
"""

from pathlib import Path

THEME_PLUGIN_PREFIX = "theme_"

SRC_DIR = Path(__file__).resolve().parents[2]
THEMES_DIR = SRC_DIR / "themes"
PLUGINS_DIR = SRC_DIR / "plugins"


def theme_plugin_slug(plugin_dir: Path) -> str | None:
    """Return the theme slug provided by a plugin directory, or None."""
    if not (plugin_dir / "theme.json").exists():
        return None
    name = plugin_dir.name
    if name.startswith(THEME_PLUGIN_PREFIX):
        return name[len(THEME_PLUGIN_PREFIX) :]
    return name


def discover_plugin_themes() -> dict[str, Path]:
    """Map every plugin-provided theme slug to its plugin directory."""
    themes: dict[str, Path] = {}
    if not PLUGINS_DIR.exists():
        return themes
    for entry in sorted(PLUGINS_DIR.iterdir()):
        if not entry.is_dir():
            continue
        slug = theme_plugin_slug(entry)
        if slug is not None and slug not in themes:
            themes[slug] = entry
    return themes


def find_theme_dir(name: str | None) -> Path | None:
    """Resolve a theme slug to its directory (built-in first, then plugins)."""
    if not name:
        return None
    builtin = THEMES_DIR / name
    if builtin.exists():
        return builtin
    return discover_plugin_themes().get(name)


def theme_template_dir(name: str | None) -> Path | None:
    theme_dir = find_theme_dir(name)
    if theme_dir is None:
        return None
    return theme_dir / "templates"


def theme_static_dir(name: str | None) -> Path | None:
    theme_dir = find_theme_dir(name)
    if theme_dir is None:
        return None
    return theme_dir / "static"


def available_theme_names() -> list[str]:
    """All theme slugs: built-in themes plus plugin-provided themes."""
    names: set[str] = set()
    if THEMES_DIR.exists():
        names.update(
            entry.name
            for entry in THEMES_DIR.iterdir()
            if entry.is_dir() and (entry / "theme.json").exists()
        )
    names.update(discover_plugin_themes())
    return sorted(names)
