import json

import pytest

from core.plugins.exceptions import PluginError, PluginVersionError
from core.plugins.models import PluginState
from tests.test_plugins.helpers import FAILING_UPGRADE_CODE, write_plugin

pytestmark = [pytest.mark.django_db]


def rewrite_version(directory, version):
    manifest_file = directory / "plugin.json"
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    manifest["version"] = version
    manifest_file.write_text(json.dumps(manifest), encoding="utf-8")


def test_upgrade_updates_version(manager, tmp_path):
    plugin_dir = tmp_path / "dummy"
    write_plugin(plugin_dir, version="1.0.0")
    manager.discover_plugins()
    manager.install_plugin("dummy")

    rewrite_version(plugin_dir, "1.1.0")
    manager.discover_plugins()
    state = manager.upgrade_plugin("dummy")

    assert state.version == "1.1.0"
    PluginState.objects.get(plugin_id="dummy").refresh_from_db()
    assert PluginState.objects.get(plugin_id="dummy").version == "1.1.0"


def test_upgrade_requires_newer_version(discovered):
    discovered.install_plugin("dummy")
    with pytest.raises(PluginVersionError):
        discovered.upgrade_plugin("dummy")


def test_failed_upgrade_keeps_old_version(manager, tmp_path):
    plugin_dir = tmp_path / "dummy"
    write_plugin(plugin_dir, version="1.0.0")
    manager.discover_plugins()
    manager.install_plugin("dummy")

    rewrite_version(plugin_dir, "2.0.0")
    plugin_dir.joinpath("plugin.py").write_text(FAILING_UPGRADE_CODE, encoding="utf-8")
    manager.discover_plugins()

    with pytest.raises(PluginError, match="failed"):
        manager.upgrade_plugin("dummy")

    assert PluginState.objects.get(plugin_id="dummy").version == "1.0.0"
