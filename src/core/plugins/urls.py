from django.urls import include, path

from core.plugins.exceptions import PluginError
from core.plugins.manager import PluginManager
from core.plugins.models import STATUS_ENABLED


def get_plugin_urlpatterns():
    try:
        manager = PluginManager()
        manager.discover_plugins()
        patterns = []
        for info in manager.list_plugins():
            if info.status == STATUS_ENABLED:
                try:
                    plugin = manager.get_class(info.plugin_id)()
                    patterns.extend(plugin.get_urls())
                except PluginError:
                    continue
        return patterns
    except Exception:
        return []


plugin_urlpatterns = get_plugin_urlpatterns()

urlpatterns = [
    path("", include(plugin_urlpatterns)),
]
