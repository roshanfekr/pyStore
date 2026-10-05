from core.plugins.base import Plugin
from plugins.shipping_dummy.provider import DummyShippingProvider


class ShippingDummyPlugin(Plugin):
    def get_shipping_providers(self):
        return [DummyShippingProvider()]

    def get_settings_defaults(self):
        return {"free_shipping_threshold": "0"}
