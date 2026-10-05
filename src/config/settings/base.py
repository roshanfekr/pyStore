import os
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()

ENV_FILE = BASE_DIR.parent / ".env"
if ENV_FILE.exists():
    env.read_env(ENV_FILE, overwrite=False)

SECRET_KEY = env.str("SECRET_KEY", default="insecure-dev-only-secret-key")

DEBUG = env.bool("DEBUG", default=False)

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

CORE_APPS = [
    "core",
]

THIRD_PARTY_APPS = [
    "rest_framework.authtoken",
]

BUSINESS_APPS = [
    "apps.identity",
    "apps.stores",
    "apps.vendors",
    "apps.catalog",
    "apps.inventory",
    "apps.pricing",
    "apps.cart",
    "apps.orders",
    "apps.checkout",
    "apps.cms",
    "apps.media",
    "apps.storefront",
    "apps.search",
    "apps.admin_panel",
]

SEARCH_BACKEND = env.str("SEARCH_BACKEND", default="database")

from core.plugins.loader import get_discovered_plugin_apps  # noqa: E402

PLUGIN_APPS = get_discovered_plugin_apps()

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + BUSINESS_APPS + CORE_APPS + PLUGIN_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "themes" / env.str("ACTIVE_THEME", default="default") / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.storefront.context_processors.storefront",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default="postgres://pystore:pystore@localhost:5432/pystore",
    )
}

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": env.str("REDIS_URL", default="redis://localhost:6379/0"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
    }
}

REDIS_URL = env.str("REDIS_URL", default="redis://localhost:6379/0")

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
    {"NAME": "apps.identity.validators.ComplexPasswordValidator"},
]

REST_FRAMEWORK = {
    "EXCEPTION_HANDLER": "core.error_handling.api_exception_handler",
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
}

AUTH_USER_MODEL = "identity.User"

AUTHENTICATION_BACKENDS = [
    "apps.identity.backends.PermissionBackend",
    "django.contrib.auth.backends.ModelBackend",
]

CELERY_BROKER_URL = env.str("CELERY_BROKER_URL", default="redis://localhost:6379/1")
CELERY_RESULT_BACKEND = env.str("CELERY_RESULT_BACKEND", default="redis://localhost:6379/2")
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TIMEZONE = "UTC"
CELERY_TASK_TRACK_STARTED = True
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_TASK_DEFAULT_QUEUE = "default"

CELERY_BEAT_SCHEDULE = env.json("CELERY_BEAT_SCHEDULE", default={})

SETTINGS_ENCRYPTION_KEY = env.str("SETTINGS_ENCRYPTION_KEY", default=None)

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_FILE_STORAGE = env.str(
    "DEFAULT_FILE_STORAGE", default="django.core.files.storage.FileSystemStorage"
)

ACTIVE_THEME = env.str("ACTIVE_THEME", default="default")

STATICFILES_DIRS = [
    dir for dir in [BASE_DIR / "themes" / ACTIVE_THEME / "static"] if dir.exists()
]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGS_DIR = BASE_DIR / "logs"
os.makedirs(LOGS_DIR, exist_ok=True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "{levelname} {asctime} [{name}] {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": env.str("LOG_LEVEL", default="INFO"),
    },
    "loggers": {
        "django": {
            "level": "INFO",
            "propagate": True,
        },
        "celery": {
            "level": "INFO",
            "propagate": True,
        },
    },
}
