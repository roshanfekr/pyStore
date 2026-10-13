# pyStore

E-commerce platform (nopCommerce-like) built with Python — Modular Monolith, Plugin-Based Architecture.

## Stack

- Python 3.10+
- Django 5.2 + Django REST Framework
- SQL Server
- Redis
- Celery
- Pytest

## Project Structure

```text
pyStore/
├── src/
│   ├── config/        # Project configuration (settings, urls, celery, wsgi/asgi)
│   │   └── settings/  # base / development / production / test
│   ├── core/          # Core framework (infrastructure, NO business domain)
│   │   └── health/    # Health check subsystem
│   ├── apps/          # Business domain apps
│   │   ├── identity/  # Users, customers, roles, granular permissions (RBAC)
│   │   ├── stores/    # Store, multi-store, domains, localization (languages/currencies)
│   │   ├── vendors/   # Vendor domain and memberships
│   │   ├── catalog/   # Products, variants, categories, brands, SEO
│   │   └── inventory/ # Warehouses, stock, reservations, audit transactions
│   └── plugins/       # Plugins (sample_plugin, theme_pacific included)
│   └── frontend/      # Vue 3 SPA storefront (Vite + Router + Pinia)
├── tests/             # Test suite (pytest)
├── scripts/           # Helper scripts
├── requirements/      # base.txt / dev.txt
└── docs/              # Documentation
```

## Quickstart (local)

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements\dev.txt
copy .env.example .env
```

Configure `DATABASE_URL` to a local SQL Server (the app uses the `mssql-django` backend and needs the Microsoft ODBC driver installed) and `REDIS_URL` to a local Redis, then:

```powershell
cd src
python manage.py migrate
python manage.py runserver
```

> Without SQL Server/Redis you can still run checks and tests (tests use SQLite in-memory + mocked Redis).

## Tests

```powershell
.\scripts\test.ps1              # run suite
.\scripts\test.ps1 -Coverage    # with coverage
```

## Storefront (hybrid SSR + Vue)

The storefront is a **hybrid**: content pages are server-rendered by Django
(themes and plugins work unchanged, good for SEO), while interactive flows are a
Vue 3 SPA (`src/frontend`, Vite + Vue Router + Pinia) that consumes the Django
REST API.

- Server-rendered (Django templates + themes/plugins): `/`, `/category/<slug>/`,
  `/product/<slug>/`, `/search/`, `/blog/…`, CMS pages.
- Vue SPA: `/cart/`, `/checkout/`, `/login/`, `/register/`, `/account/`,
  `/wishlist/`, `/compare/`, `/orders/<number>/`.

The two share the Django session, so the guest cart and login state are
consistent across server-rendered and SPA pages (an API login also establishes
the session). The SPA is used for the interactive routes when
`STOREFRONT_SPA_ENABLED=True` (the default in `development`); set it to `False`
to fall back to the server-rendered versions of those pages.

Build and run:

```powershell
cd src\frontend
npm install
npm run build     # emits into src\apps\storefront\static\storefront-spa
```

Then start Django as usual (`python manage.py runserver`). Until the frontend is
built, the interactive routes return a short "not built" page instead of failing.

For live development, run `npm run dev` (Vite on http://localhost:5173, proxying
`/api`, `/static` and `/admin` to Django) alongside `python manage.py runserver`.

## Theme Plugins

Like nopCommerce, themes ship as plugins. A plugin directory under `src/plugins/` becomes a theme when it contains a `theme.json` manifest plus `templates/` and `static/` assets; the theme slug is the directory name without the `theme_` prefix (e.g. `plugins/theme_pacific` → theme `pacific`). Built-in themes in `src/themes/` take precedence over plugin themes with the same slug.

- Install/enable the plugin through the plugin engine (it appears in the admin plugin list).
- Activate it with `ACTIVE_THEME=pacific` in `.env`.
- Customize copy/colors either in `theme.json` `config` or through plugin settings (`PluginState.settings`), which override the manifest.

## Health Check

`GET /health/` reports the status of:

- `application`
- `database`
- `redis`

Returns `200 {"status": "ok"}` when all components are healthy, otherwise `503 {"status": "degraded"}` with the failing component marked `"error"`.

## Phase Status

| Phase | Title | Status |
|-------|-------|--------|
| 00 | Project Foundation | ✅ |
| 01 | Core Architecture | ✅ |
| 02 | Plugin Engine | ✅ |
| 03 | Settings / Events / Cache / Jobs | ✅ |
| 04 | Identity / Users / Roles / Permissions | ✅ |
| 05 | Store / Multi-Store / Vendor | ✅ |
| 06 | Catalog / Product | ✅ |
| 07 | Product Attributes / Inventory | ✅ |
| 08 | Pricing / Tax / Discount | ✅ |
| 09 | Cart / Wishlist / Compare | ✅ |
| 10 | Checkout | ✅ |
| 11 | Order Management | ✅ |
| 12 | Payment / Shipping Plugin System | ✅ |
| 13 | CMS / Media / SEO | ✅ |
| 14 | Storefront / Theme System | ✅ |
| 15 | Search | ✅ |
| 16 | Admin Panel | ✅ |
