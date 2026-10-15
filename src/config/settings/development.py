from .base import *  # noqa: F403

DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "testserver"]

# Serve the Vue storefront SPA by default in development.
STOREFRONT_SPA_ENABLED = env.bool("STOREFRONT_SPA_ENABLED", default=True)

# Local development is self-contained by default: without a running Redis the
# API (rate throttling uses the cache) and background tasks would fail. Use an
# in-process cache and run Celery tasks eagerly unless DEV_USE_REDIS=True.
if not env.bool("DEV_USE_REDIS", default=False):
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        }
    }
    CELERY_TASK_ALWAYS_EAGER = True

LOGGING["handlers"]["file"] = {
    "class": "logging.handlers.RotatingFileHandler",
    "filename": str(LOGS_DIR / "pystore.log"),
    "maxBytes": 5 * 1024 * 1024,
    "backupCount": 5,
    "encoding": "utf-8",
    "formatter": "standard",
}
LOGGING["root"]["handlers"] = ["console", "file"]
