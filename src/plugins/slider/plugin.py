from core.plugins.base import Plugin
from plugins.slider.settings import DEFAULTS, SCHEMA


class SliderPlugin(Plugin):
    def get_storefront_hooks(self):
        return {"home_middle": ["slider/slider.html"]}

    def get_settings_defaults(self):
        return dict(DEFAULTS)

    def get_settings_schema(self):
        return dict(SCHEMA)
