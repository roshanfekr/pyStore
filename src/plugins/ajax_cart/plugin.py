from core.plugins.base import Plugin
from plugins.ajax_cart.settings import DEFAULTS, SCHEMA


class AjaxCartPlugin(Plugin):
    def get_storefront_hooks(self):
        return {
            "head": ["ajax_cart/head.html"],
            "header_cart": ["ajax_cart/cart_button.html"],
            "body_end": ["ajax_cart/drawer.html"],
            "cart_page": ["ajax_cart/cart_page.html"],
        }

    def get_settings_defaults(self):
        return dict(DEFAULTS)

    def get_settings_schema(self):
        return dict(SCHEMA)
