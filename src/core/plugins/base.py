class Plugin:
    def __init__(self):
        self._settings_config: dict = {}

    def configure(self, config: dict) -> None:
        self._settings_config = dict(config or {})

    def on_install(self):
        pass

    def on_uninstall(self):
        pass

    def on_enable(self):
        pass

    def on_disable(self):
        pass

    def on_upgrade(self, from_version: str, to_version: str):
        pass

    def get_urls(self):
        return []

    def get_admin_urls(self):
        return []

    def get_event_handlers(self):
        return {}

    def get_permissions(self):
        return []

    def get_services(self):
        return {}

    def get_settings_defaults(self):
        return {}

    def get_payment_gateways(self):
        return []

    def get_shipping_providers(self):
        return []

    def get_notification_providers(self):
        return []
