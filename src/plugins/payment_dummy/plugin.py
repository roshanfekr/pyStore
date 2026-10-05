from core.plugins.base import Plugin
from plugins.payment_dummy.gateway import DummyGateway


class PaymentDummyPlugin(Plugin):
    def get_payment_gateways(self):
        gateway = DummyGateway()
        gateway.configure(self._settings_config)
        return [gateway]

    def get_settings_defaults(self):
        return {"merchant_id": "dummy-merchant", "auto_capture": True}
