from pathlib import Path

from django.conf import settings

SRC_DIR = Path(settings.BASE_DIR)
THEMES_DIR = SRC_DIR / "themes"


def get_active_theme_name() -> str:
    return getattr(settings, "ACTIVE_THEME", "default")


def get_theme_dir(name: str | None = None) -> Path:
    return THEMES_DIR / (name or get_active_theme_name())


def list_themes() -> list[str]:
    if not THEMES_DIR.exists():
        return []
    return sorted(
        entry.name
        for entry in THEMES_DIR.iterdir()
        if entry.is_dir() and (entry / "theme.json").exists()
    )


def get_theme_manifest(name: str | None = None) -> dict:
    import json

    manifest_file = get_theme_dir(name) / "theme.json"
    if not manifest_file.exists():
        return {}
    try:
        return json.loads(manifest_file.read_text(encoding="utf-8"))
    except Exception:
        return {}


def get_theme_config(name: str | None = None) -> dict:
    manifest = get_theme_manifest(name)
    return dict(manifest.get("config", {}))


def get_theme_static_dir(name: str | None = None) -> Path:
    return get_theme_dir(name) / "static"
