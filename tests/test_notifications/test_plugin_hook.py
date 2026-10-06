import json

import pytest

from core.notifications.registry import notification_provider_registry
from core.plugins.manager import PluginManager

pytestmark = [pytest.mark.django_db]

NOTIFICATION_PLUGIN_CODE = """
from core.notifications.interface import NotificationProvider, NotificationSendResult
from core.plugins.base import Plugin as BasePlugin


class DummySMSProvider(NotificationProvider):
    code = "dummy_sms"
    name = "Dummy SMS"
    channel = "sms"

    def send(self, message):
        return NotificationSendResult(successful=True, reference="dummy-sms")


class Plugin(BasePlugin):
    def get_notification_providers(self):
        return [DummySMSProvider()]
"""


def write_notification_plugin(directory, plugin_id="notification_dummy"):
    directory.mkdir(parents=True, exist_ok=True)
    manifest = {
        "id": plugin_id,
        "name": plugin_id.replace("_", " ").title(),
        "version": "1.0.0",
        "author": "test",
        "description": f"test plugin {plugin_id}",
        "dependencies": [],
        "entry_point": "plugin:Plugin",
    }
    (directory / "plugin.json").write_text(json.dumps(manifest), encoding="utf-8")
    (directory / "plugin.py").write_text(NOTIFICATION_PLUGIN_CODE, encoding="utf-8")
    return directory


@pytest.fixture
def plugin_manager(tmp_path, db):
    manager = PluginManager(plugins_dir=tmp_path)
    write_notification_plugin(tmp_path / "notification_dummy")
    manager.discover_plugins()
    return manager


def test_plugin_provider_registered_on_enable(plugin_manager):
    if plugin_manager._state("notification_dummy") is None:
        plugin_manager.install_plugin("notification_dummy")
    plugin_manager.enable_plugin("notification_dummy")

    provider = notification_provider_registry.get("dummy_sms")
    assert provider is not None
    assert provider.channel == "sms"


def test_plugin_provider_unregistered_on_disable(plugin_manager):
    if plugin_manager._state("notification_dummy") is None:
        plugin_manager.install_plugin("notification_dummy")
    plugin_manager.enable_plugin("notification_dummy")
    assert notification_provider_registry.get("dummy_sms") is not None

    plugin_manager.disable_plugin("notification_dummy")
    assert notification_provider_registry.get("dummy_sms") is None
