"""Default theme configuration.

Mirrors the ``config`` block of ``theme.json``. Values stored through the
plugin settings API (``PluginState.settings``) override these defaults and
the theme manifest, in that order.
"""

DEFAULTS = {
    "site_name": "pyStore",
    "primary_color": "#0e7490",
    "accent_color": "#22d3ee",
    "announcement_text": "Free shipping on orders over $50 — dive in!",
    "hero_title": "Explore the Pacific",
    "hero_subtitle": "Hand-picked products, delivered with the calm of the ocean.",
    "footer_about": "pyStore — a modern e-commerce platform with a Pacific breeze.",
}
