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

    def get_storefront_hooks(self):
        """Map storefront hook names to template partials.

        Example: {"home_middle": ["slider/slider.html"]}
        """
        return {}

    def get_hook_context(self, hook_name: str) -> dict:
        """Extra template context for a storefront hook partial."""
        return {}

    def get_settings_schema(self):
        """Declarative settings fields for the admin settings page.

        Example: {"autoplay_ms": {"label": "Autoplay (ms)", "type": "integer"}}
        Supported types: string, text, integer, boolean.
        """
        return {}

    def get_price_modifiers(self):
        """Callables that can adjust the final sale price of a product.

        Each modifier receives ``(product, variant, price, context)`` and
        returns either the new price (Decimal) or None to keep the current
        price. Modifiers of enabled plugins are applied in plugin id order
        after the pricing provider (price lists, scheduled prices).
        """
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
