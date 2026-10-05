# pyStore

E-commerce platform (nopCommerce-like) built with Python — Modular Monolith, Plugin-Based Architecture.

## Stack

- Python 3.10+
- Django 5.2 + Django REST Framework
- PostgreSQL
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
│   │   ├── stores/    # Store, multi-store, domains, localization
│   │   ├── vendors/   # Vendor domain and memberships
│   │   ├── catalog/   # Products, variants, categories, brands, SEO
│   │   └── inventory/ # Warehouses, stock, reservations, audit transactions
│   └── plugins/       # Plugins (sample_plugin included)
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

Configure `DATABASE_URL` to a local PostgreSQL and `REDIS_URL` to a local Redis, then:

```powershell
cd src
python manage.py migrate
python manage.py runserver
```

> Without PostgreSQL/Redis you can still run checks and tests (tests use SQLite in-memory + mocked Redis).

## Tests

```powershell
.\scripts\test.ps1              # run suite
.\scripts\test.ps1 -Coverage    # with coverage
```

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
