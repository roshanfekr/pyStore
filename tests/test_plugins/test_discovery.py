import json

import pytest

from core.plugins.models import PluginState
from tests.test_plugins.helpers import write_plugin

pytestmark = [pytest.mark.django_db]


def test_discover_finds_valid_plugin(manager, tmp_path):
    write_plugin(tmp_path / "dummy")
    assert manager.discover_plugins() == ["dummy"]
    assert manager.errors == []
    info = manager.get_plugin("dummy")
    assert info.plugin_id == "dummy"
    assert info.version == "1.0.0"
    assert info.status == "not_installed"


def test_discover_ignores_dirs_without_manifest(manager, tmp_path):
    (tmp_path / "not_a_plugin").mkdir()
    assert manager.discover_plugins() == []


def test_discover_reports_invalid_manifest(manager, tmp_path):
    directory = tmp_path / "broken"
    directory.mkdir()
    (directory / "plugin.json").write_text(json.dumps({"id": "broken"}), encoding="utf-8")

    manager.discover_plugins()

    assert manager.registry.all() == []
    assert "broken" in manager.errors[0]


def test_discover_reports_invalid_version(manager, tmp_path):
    write_plugin(tmp_path / "broken", version="not-a-version")

    manager.discover_plugins()

    assert manager.registry.all() == []
    assert "not-a-version" in manager.errors[0]


def test_discover_reports_duplicate_plugin_id(manager, tmp_path):
    write_plugin(tmp_path / "first", plugin_id="dummy")
    write_plugin(tmp_path / "second", plugin_id="dummy")

    ids = manager.discover_plugins()

    assert ids == ["dummy"]
    assert any("duplicate" in error for error in manager.errors)


def test_list_plugins_merges_disk_and_db(manager, tmp_path):
    write_plugin(tmp_path / "dummy")
    manager.discover_plugins()
    manager.install_plugin("dummy")

    infos = {info.plugin_id: info for info in manager.list_plugins()}

    assert infos["dummy"].status == "installed"
    assert infos["dummy"].version == "1.0.0"


def test_orphaned_state_is_reported(manager, tmp_path, db):
    write_plugin(tmp_path / "dummy")
    manager.discover_plugins()
    PluginState.objects.create(plugin_id="ghost", name="Ghost", version="0.1.0")

    infos = {info.plugin_id: info for info in manager.list_plugins()}

    assert infos["ghost"].status == "installed"
    assert "not found" in infos["ghost"].description
