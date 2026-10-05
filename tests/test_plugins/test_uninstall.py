import pytest

from core.plugins.exceptions import PluginDependencyError, PluginError
from core.plugins.models import PluginState
from tests.test_plugins.helpers import write_plugin

pytestmark = [pytest.mark.django_db]


def test_uninstall_requires_disable_first(discovered):
    discovered.install_plugin("dummy")
    with pytest.raises(PluginError):
        discovered.uninstall_plugin("dummy")


def test_uninstall_blocked_by_installed_dependent(manager, tmp_path):
    write_plugin(tmp_path / "parent", plugin_id="parent")
    write_plugin(tmp_path / "child", plugin_id="child", deps=["parent"])
    manager.discover_plugins()
    manager.install_plugin("parent")
    manager.enable_plugin("parent")
    manager.install_plugin("child")

    manager.disable_plugin("parent")
    with pytest.raises(PluginDependencyError):
        manager.uninstall_plugin("parent")

    assert PluginState.objects.filter(plugin_id="parent").exists()


def test_uninstall_removes_state(discovered):
    discovered.install_plugin("dummy")
    discovered.enable_plugin("dummy")
    discovered.disable_plugin("dummy")
    discovered.uninstall_plugin("dummy")
    assert PluginState.objects.filter(plugin_id="dummy").exists() is False
