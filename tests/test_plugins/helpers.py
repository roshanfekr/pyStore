import json

SIMPLE_PLUGIN_CODE = """
from core.plugins.base import Plugin as BasePlugin


class Plugin(BasePlugin):
    pass
"""

DEFAULTS_PLUGIN_CODE = """
from core.plugins.base import Plugin as BasePlugin


class Plugin(BasePlugin):
    def get_settings_defaults(self):
        return {"greeting": "Hello", "target": "World"}
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
