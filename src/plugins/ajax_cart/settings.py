DEFAULTS = {
    "open_drawer_on_add": True,
    "show_header_badge": True,
    "accent_color": "",
    "free_shipping_threshold": "",
    "empty_message": "Your cart is empty.",
    "checkout_label": "Checkout",
}

SCHEMA = {
    "open_drawer_on_add": {
        "label": "Open drawer after add",
        "type": "boolean",
        "help": "Open the cart drawer automatically when a product is added via AJAX.",
    },
    "show_header_badge": {
        "label": "Show header cart badge",
        "type": "boolean",
        "help": "Show the item count badge on the header cart button.",
    },
    "accent_color": {
        "label": "Accent color (hex)",
        "type": "string",
        "help": "Optional override for the drawer accent. Leave blank to use the theme primary color.",
    },
    "free_shipping_threshold": {
        "label": "Free shipping threshold",
        "type": "string",
        "help": "Optional amount. When set, the drawer shows a free-shipping progress line.",
    },
    "empty_message": {
        "label": "Empty cart message",
        "type": "string",
        "help": "Message shown when the cart has no items.",
    },
    "checkout_label": {
        "label": "Checkout button label",
        "type": "string",
        "help": "Label of the checkout button in the drawer and cart page.",
    },
}
