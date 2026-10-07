from .base import *  # noqa: F403

DEBUG = True

ACTIVE_THEME = "default"

# TEMPLATES DIRS / STATICFILES_DIRS were resolved from ACTIVE_THEME in base;
# pin them to the default theme so tests ignore the developer's .env.
from core.plugins import theme_discovery  # noqa: E402

TEMPLATES = [dict(template) for template in TEMPLATES]
TEMPLATES[0]["DIRS"] = [
    dir
    for dir in [BASE_DIR / "templates", theme_discovery.theme_template_dir("default")]
    if dir is not None and dir.exists()
]
STATICFILES_DIRS = [
    dir for dir in [theme_discovery.theme_static_dir("default")] if dir is not None and dir.exists()
]

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

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
DEFAULT_FROM_EMAIL = "no-reply@test.local"

REST_FRAMEWORK = {**REST_FRAMEWORK, "DEFAULT_THROTTLE_CLASSES": []}

CELERY_TASK_ALWAYS_EAGER = True

CELERY_TASK_EAGER_PROPAGATES = True

LOGGING["root"]["level"] = "WARNING"
