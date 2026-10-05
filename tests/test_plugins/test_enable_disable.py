import sys

import pytest

from core.plugins.exceptions import PluginDependencyError, PluginError
from core.plugins.models import PluginState
from tests.test_plugins.helpers import EVENT_PLUGIN_CODE, write_plugin

pytestmark = [pytest.mark.django_db]


def test_enable_registers_services_events_permissions(manager, tmp_path, box, bus, perms):
    write_plugin(tmp_path / "dummy", code=EVENT_PLUGIN_CODE)
    manager.discover_plugins()
    manager.install_plugin("dummy")
    manager.enable_plugin("dummy")

    assert box.resolve("dummy.greeter") is not None
    assert perms.for_plugin("dummy") == ["dummy.view"]

    event_type, _handler = manager._event_registrations["dummy"][0]
    module = sys.modules[event_type.__module__]

    bus.dispatch(event_type())
    assert module.fired

    manager.disable_plugin("dummy")
    with pytest.raises(KeyError):
        box.resolve("dummy.greeter")
    assert perms.for_plugin("dummy") == []
    assert bus.get_handlers(event_type) == []

    module.fired.clear()
    bus.dispatch(module.Pinged())
    assert module.fired == []


def test_enable_without_install_raises(manager, tmp_path):
    write_plugin(tmp_path / "dummy")
    manager.discover_plugins()

    with pytest.raises(PluginError):
        manager.enable_plugin("dummy")


def test_enable_twice_raises(discovered):
    discovered.install_plugin("dummy")
    discovered.enable_plugin("dummy")
    with pytest.raises(PluginError):
        discovered.enable_plugin("dummy")


def test_enable_requires_enabled_dependencies(manager, tmp_path):
    write_plugin(tmp_path / "parent", plugin_id="parent")
    write_plugin(tmp_path / "child", plugin_id="child", deps=["parent"])
    manager.discover_plugins()
    manager.install_plugin("parent")
    manager.install_plugin("child")

    with pytest.raises(PluginDependencyError):
        manager.enable_plugin("child")

    manager.enable_plugin("parent")
    manager.enable_plugin("child")
    assert PluginState.objects.get(plugin_id="child").status == "enabled"

def test_disable_without_enable_raises(discovered):
    discovered.install_plugin("dummy")
    with pytest.raises(PluginError):
        discovered.disable_plugin("dummy")


def test_disable_blocked_by_enabled_dependent(manager, tmp_path):
    write_plugin(tmp_path / "parent", plugin_id="parent")
    write_plugin(tmp_path / "child", plugin_id="child", deps=["parent"])
    manager.discover_plugins()
    manager.install_plugin("parent")
    manager.enable_plugin("parent")
    manager.install_plugin("child")
    manager.enable_plugin("child")

    with pytest.raises(PluginDependencyError):
        manager.disable_plugin("parent")
