DEFAULTS = {
    "images": (
        "/static/slider/img/slide1.svg | Fresh drops every week\n"
        "/static/slider/img/slide2.svg | Up to 40% off summer collection\n"
        "/static/slider/img/slide3.svg | Free shipping on orders over $50"
    ),
    "autoplay_ms": 5000,
    "height": 380,
    "show_arrows": True,
    "show_indicators": True,
}

SCHEMA = {
    "images": {
        "label": "Slide images",
        "type": "text",
        "help": "One image URL per line. Optional caption after a pipe: /path/image.jpg | Caption text",
    },
    "autoplay_ms": {
        "label": "Autoplay interval (ms)",
        "type": "integer",
        "help": "Delay between slides in milliseconds. Use 0 to disable autoplay.",
    },
    "height": {
        "label": "Slider height (px)",
        "type": "integer",
        "help": "Height of the slider area in pixels.",
    },
    "show_arrows": {"label": "Show prev/next arrows", "type": "boolean"},
    "show_indicators": {"label": "Show position indicators", "type": "boolean"},
}
