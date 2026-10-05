import pytest

from core.plugins.exceptions import (
    PluginAlreadyInstalledError,
    PluginDependencyError,
    PluginError,
    PluginVersionError,
)
from core.plugins.models import PluginState
from tests.test_plugins.helpers import (
    FAILING_INSTALL_CODE,
    write_plugin,
)

pytestmark = [pytest.mark.django_db]


def test_install_creates_installed_state(discovered):
    state = discovered.install_plugin("dummy")
    assert state.status == "installed"
    assert state.version == "1.0.0"
    assert PluginState.objects.filter(plugin_id="dummy").exists()


def test_install_twice_raises(discovered):
    discovered.install_plugin("dummy")
    with pytest.raises(PluginAlreadyInstalledError):
        discovered.install_plugin("dummy")


def test_install_with_missing_dependency_fails(manager, tmp_path):
    write_plugin(tmp_path / "child", plugin_id="child", deps=["parent"])
    manager.discover_plugins()

    with pytest.raises(PluginDependencyError):
        manager.install_plugin("child")

    assert PluginState.objects.filter(plugin_id="child").exists() is False


def test_install_requires_dependency_installed(manager, tmp_path):
    write_plugin(tmp_path / "parent", plugin_id="parent")
    write_plugin(tmp_path / "child", plugin_id="child", deps=["parent"])
    manager.discover_plugins()

    with pytest.raises(PluginDependencyError):
        manager.install_plugin("child")

    manager.install_plugin("parent")
    manager.install_plugin("child")
    assert PluginState.objects.get(plugin_id="child").status == "installed"


def test_install_with_future_core_version_fails(manager, tmp_path):
    write_plugin(
        tmp_path / "picky", plugin_id="picky", manifest_extra={"minimum_core_version": "999.0.0"}
    )
    manager.discover_plugins()

    with pytest.raises(PluginVersionError):
        manager.install_plugin("picky")


def test_failed_installation_leaves_no_state(manager, tmp_path):
    write_plugin(tmp_path / "bad", plugin_id="bad", code=FAILING_INSTALL_CODE)
    manager.discover_plugins()

    with pytest.raises(PluginError, match="failed"):
        manager.install_plugin("bad")

    assert PluginState.objects.filter(plugin_id="bad").exists() is False
