import pytest
from django.conf import settings
from django.test import override_settings

from apps.storefront.themes import (
    get_theme_config,
    get_theme_dir,
    get_theme_manifest,
    get_theme_plugin_id,
    list_themes,
)
from apps.stores.services import create_store
from core.plugins.manager import PluginManager
from core.plugins.models import STATUS_ENABLED, PluginState

pytestmark = [pytest.mark.django_db]

PACIFIC_TEMPLATES_MARKER = "pacific-hero"


@pytest.fixture
def store(db):
    return create_store("Pacific Theme Store")


def test_pacific_theme_is_discovered_from_plugin():
    assert "pacific" in list_themes()

    theme_dir = get_theme_dir("pacific")
    assert theme_dir == settings.BASE_DIR / "plugins" / "theme_pacific"
    assert (theme_dir / "theme.json").exists()

    manifest = get_theme_manifest("pacific")
    assert manifest["name"] == "Pacific"
    assert get_theme_plugin_id("pacific") == "theme_pacific"


def test_pacific_theme_config_defaults():
    config = get_theme_config("pacific")
    assert config["site_name"] == "pyStore"
    assert config["hero_title"] == "Explore the Pacific"
    assert config["primary_color"] == "#0e7490"


def test_pacific_theme_config_merges_plugin_settings():
    PluginState.objects.create(
        plugin_id="theme_pacific",
        name="Pacific Theme",
        version="1.0.0",
        settings={"hero_title": "Custom Hero"},
    )

    config = get_theme_config("pacific")
    assert config["hero_title"] == "Custom Hero"
    assert config["primary_color"] == "#0e7490"

    assert "hero_title" not in get_theme_config("default")


def test_pacific_theme_plugin_lifecycle():
    manager = PluginManager()
    manager.discover_plugins()

    assert manager.errors == []
    assert "theme_pacific" in manager.registry.ids()

    manager.install_plugin("theme_pacific")
    manager.enable_plugin("theme_pacific")

    info = manager.get_plugin("theme_pacific")
    assert info.status == STATUS_ENABLED

    defaults = manager.get_settings("theme_pacific")
    assert defaults["hero_title"] == "Explore the Pacific"


def test_pacific_theme_renders_when_active(client, store, settings):
    pacific_templates = str(get_theme_dir("pacific") / "templates")
    templates = [dict(t) for t in settings.TEMPLATES]
    templates[0] = {**templates[0], "DIRS": [pacific_templates]}

    with override_settings(TEMPLATES=templates, ACTIVE_THEME="pacific"):
        response = client.get("/")
        content = response.content.decode()
        assert PACIFIC_TEMPLATES_MARKER in content
        assert "Explore the Pacific" in content
        assert "pacific-footer" in content


def test_pacific_theme_templates_override_storefront_defaults(client, store, settings):
    pacific_templates = str(get_theme_dir("pacific") / "templates")
    templates = [dict(t) for t in settings.TEMPLATES]
    templates[0] = {
        **templates[0],
        "DIRS": [str(settings.BASE_DIR / "templates"), pacific_templates],
    }

    with override_settings(TEMPLATES=templates, ACTIVE_THEME="pacific"):
        response = client.get("/")
        content = response.content.decode()
        assert "Free shipping on orders over $50" in content
        assert "Pacific theme, all rights reserved" in content


def test_pacific_plugin_app_is_installed():
    assert "plugins.theme_pacific" in settings.INSTALLED_APPS
    plugin_dir = settings.BASE_DIR / "plugins" / "theme_pacific"
    assert (plugin_dir / "static" / "pacific" / "css" / "pacific.css").exists()
