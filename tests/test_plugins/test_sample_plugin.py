import pytest

from core.infrastructure.dependency import container as global_container
from core.plugins.loader import get_discovered_plugin_apps
from core.plugins.manager import PluginManager
from core.plugins.models import PluginState
from core.plugins.permissions import permission_registry

pytestmark = [pytest.mark.django_db]


def test_sample_plugin_full_lifecycle():
    manager = PluginManager()
    assert "sample_plugin" in manager.discover_plugins()

    from plugins.sample_plugin.events import SamplePing, pings
    from plugins.sample_plugin.models import SampleData

    try:
        manager.install_plugin("sample_plugin")
        assert SampleData.objects.exists()

        manager.enable_plugin("sample_plugin")
        assert global_container.resolve("sample_plugin.greeter").greet() == "Hello, World!"
        assert permission_registry.for_plugin("sample_plugin") == ["sample_plugin.view_greeting"]

        pings_before = len(pings)
        manager.event_dispatcher.dispatch(SamplePing())
        assert len(pings) > pings_before

        assert manager.get_settings("sample_plugin") == {"greeting": "Hello", "target": "World"}
        assert manager.get_class("sample_plugin")().get_urls()

        manager.disable_plugin("sample_plugin")
        with pytest.raises(KeyError):
            global_container.resolve("sample_plugin.greeter")

        manager.uninstall_plugin("sample_plugin")
        assert PluginState.objects.filter(plugin_id="sample_plugin").exists() is False
    finally:
        pings.clear()
        global_container.unregister("sample_plugin.greeter")
        permission_registry.unregister("sample_plugin")
        PluginState.objects.filter(plugin_id="sample_plugin").delete()


def test_sample_plugin_model_soft_delete(db):
    from plugins.sample_plugin.models import SampleData

    sample = SampleData.objects.create(message="hi")
    sample.delete()
    assert SampleData.objects.filter(pk=sample.pk).exists() is False
    assert SampleData.all_objects.filter(pk=sample.pk).exists()


def test_loader_discovers_plugin_apps_from_disk():
    assert "plugins.sample_plugin" in get_discovered_plugin_apps()
