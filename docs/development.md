# Development Guide

## Settings Modules

- `config.settings.base` — shared settings, reads environment variables (via `django-environ`, `.env` at repo root).
- `config.settings.development` — default for `manage.py`, DEBUG on, file logging to `src/logs/`.
- `config.settings.production` — DEBUG off, HTTPS/HSTS/secure cookies enabled. Select with `DJANGO_SETTINGS_MODULE=config.settings.production`.
- `config.settings.test` — used by pytest: SQLite in-memory, LocMem cache, eager Celery, fast password hasher.

## Environment Variables

See `.env.example`. Keys: `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `DATABASE_URL`, `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`, `LOG_LEVEL`.

## Conventions

- Business logic lives in services, never in views/serializers.
- `core/` contains only infrastructure; no shop domain models.
- All database changes via versioned, reversible Django migrations.
- Type hints on all public functions; no secrets in the repository.
- Every feature ships with pytest tests; run `.\scripts\test.ps1` before delivery.

## Adding a Business App (future phases)

Create the package under `src/apps/<name>/` with the app inside `apps.<name>`, register it in `INSTALLED_APPS`, and keep domain events, services, and repositories in the architecture's designated layers.
