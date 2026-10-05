import json

import pytest

from core.events import EventDispatcher
from core.infrastructure import DependencyContainer
from core.plugins.manager import PluginManager
from core.plugins.permissions import PermissionRegistry

SIMPLE_PLUGIN_CODE = """
from core.plugins.base import Plugin as BasePlugin


class Plugin(BasePlugin):
    pass
"""

FAILING_INSTALL_CODE = """
from core.plugins.base import Plugin as BasePlugin


class Plugin(BasePlugin):
    def on_install(self):
        raise ValueError("boom install")
"""

FAILING_UPGRADE_CODE = """
from core.plugins.base import Plugin as BasePlugin


class Plugin(BasePlugin):
    def on_upgrade(self, from_version, to_version):
        raise ValueError("boom upgrade")
"""

EVENT_PLUGIN_CODE = """
from core.events import DomainEvent
from core.plugins.base import Plugin as BasePlugin


class Pinged(DomainEvent):
    pass


fired = []


def on_ping(event):
    fired.append(event.event_id)


class Plugin(BasePlugin):
    def get_event_handlers(self):
        return {Pinged: [on_ping]}

    def get_services(self):
        return {"dummy.greeter": lambda: object()}

    def get_permissions(self):
        return ["dummy.view"]
"""


def write_plugin(
    directory,
    plugin_id="dummy",
    version="1.0.0",
    deps=None,
    code=SIMPLE_PLUGIN_CODE,
    manifest_extra=None,
):
    directory.mkdir(parents=True, exist_ok=True)
    manifest = {
        "id": plugin_id,
        "name": plugin_id.replace("_", " ").title(),
        "version": version,
        "author": "test",
        "description": f"test plugin {plugin_id}",
        "dependencies": deps or [],
        "entry_point": "plugin:Plugin",
    }
    manifest.update(manifest_extra or {})
    (directory / "plugin.json").write_text(json.dumps(manifest), encoding="utf-8")
    (directory / "plugin.py").write_text(code, encoding="utf-8")
    return directory


def make_manager(tmp_path, box=None, bus=None, perms=None):
    return PluginManager(
        plugins_dir=tmp_path,
        services_container=box if box is not None else DependencyContainer(),
        event_dispatcher=bus if bus is not None else EventDispatcher(),
        permissions=perms if perms is not None else PermissionRegistry(),
    )


@pytest.fixture
def box():
    return DependencyContainer()


@pytest.fixture
def bus():
    return EventDispatcher()


@pytest.fixture
def perms():
    return PermissionRegistry()


@pytest.fixture
def manager(tmp_path, box, bus, perms):
    return make_manager(tmp_path, box, bus, perms)


@pytest.fixture
def discovered(manager, tmp_path):
    write_plugin(tmp_path / "dummy")
    manager.discover_plugins()
    return manager
