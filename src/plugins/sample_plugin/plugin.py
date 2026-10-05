from core.plugins.base import Plugin
from plugins.sample_plugin.events import SamplePing, on_ping
from plugins.sample_plugin.models import SampleData
from plugins.sample_plugin.routes import urlpatterns
from plugins.sample_plugin.services import greeter_factory


class SamplePlugin(Plugin):
    def on_install(self):
        SampleData.objects.create(message="Sample plugin installed")

    def on_uninstall(self):
        SampleData.objects.all().delete()

    def get_urls(self):
        return list(urlpatterns)

    def get_event_handlers(self):
        return {SamplePing: [on_ping]}

    def get_permissions(self):
        return ["sample_plugin.view_greeting"]

    def get_services(self):
        return {"sample_plugin.greeter": greeter_factory}

    def get_settings_defaults(self):
        return {"greeting": "Hello", "target": "World"}
