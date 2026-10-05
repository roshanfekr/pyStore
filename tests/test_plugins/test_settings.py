import pytest
from django.conf import settings as django_settings

from core.plugins.models import PluginState
from tests.test_plugins.helpers import DEFAULTS_PLUGIN_CODE, write_plugin

pytestmark = [pytest.mark.django_db]


def test_settings_default_merge(manager, tmp_path):
    write_plugin(tmp_path / "dummy", code=DEFAULTS_PLUGIN_CODE)
    manager.discover_plugins()
    manager.install_plugin("dummy")

    assert manager.get_settings("dummy") == {"greeting": "Hello", "target": "World"}


def test_set_settings_persists_and_merges(manager, tmp_path):
    write_plugin(tmp_path / "dummy", code=DEFAULTS_PLUGIN_CODE)
    manager.discover_plugins()
    manager.install_plugin("dummy")

    merged = manager.set_settings("dummy", {"greeting": "Salam"})

    assert merged == {"greeting": "Salam", "target": "World"}
    assert PluginState.objects.get(plugin_id="dummy").settings == {"greeting": "Salam"}


def test_plugin_settings_are_separate_from_global_settings(manager, tmp_path):
    code = """
from core.plugins.base import Plugin as BasePlugin


class Plugin(BasePlugin):
    def get_settings_defaults(self):
        return {"PLUGIN_SECRET": "plugin-only-secret"}
"""
    write_plugin(tmp_path / "dummy", code=code)
    manager.discover_plugins()
    manager.install_plugin("dummy")

    assert manager.get_settings("dummy") == {"PLUGIN_SECRET": "plugin-only-secret"}
    assert not hasattr(django_settings, "PLUGIN_SECRET")
