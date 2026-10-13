from .base import *  # noqa: F403

DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "testserver"]

# Serve the Vue storefront SPA by default in development.
STOREFRONT_SPA_ENABLED = env.bool("STOREFRONT_SPA_ENABLED", default=True)

LOGGING["handlers"]["file"] = {
    "class": "logging.handlers.RotatingFileHandler",
    "filename": str(LOGS_DIR / "pystore.log"),
    "maxBytes": 5 * 1024 * 1024,
    "backupCount": 5,
    "encoding": "utf-8",
    "formatter": "standard",
}
LOGGING["root"]["handlers"] = ["console", "file"]
