from .base import *  # noqa: F403

DEBUG = True

INSTALLED_APPS = list(INSTALLED_APPS) + ["tests.testapp"]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

CELERY_TASK_ALWAYS_EAGER = True

CELERY_TASK_EAGER_PROPAGATES = True

LOGGING["root"]["level"] = "WARNING"
