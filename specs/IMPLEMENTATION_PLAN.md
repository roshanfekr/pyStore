# Implementation Plan — pyStore V1

**Document:** `specs/IMPLEMENTATION_PLAN.md`\
**Version:** 0.7\
**Status:** Draft — prepared for user review. This document does **not**
authorize implementation: each phase starts only when the user authorizes it
(`specs/README.md` §7, Phase 4/5 gates). Revision 0.2 (2026-10-22) restructures
P0 into staged, non-blocking activities with explicit exit criteria and records
the P0 baseline measurement results (§4.1). Revision 0.3 (2026-10-22) closes
the P0 documentation activities P0.2, P0.3, and P0.4 against that recorded
evidence, records P0.3 as partially complete with its remaining blocker, and
leaves SQL Server and Redis/Celery runtime validation scheduled in P8.
Revision 0.4 (2026-10-22) records the first implementation increment: the
customer address book (FR-CUST-002, FR-CHK-001, AC-CUST-002, AC-CHK-002)
delivered through the API-first backend, with the storefront surface still
outstanding. Revision 0.5 (2026-10-22) records the brand data and public
visibility increment (FR-CAT-007 and the FR-CAT-006 exposure clause); the
brand listing and detail pages remain outstanding. Revision 0.6 (2026-10-22)
records the first migrated content route: the brand listing and brand detail
pages in the Vue storefront (P4), with their remaining gaps. Revision 0.7
(2026-10-22) records the category route migration and the Vitest component
test harness.\
**Last updated:** 2026-10-22\
**Basis:** `PROJECT_SCOPE.md` v0.10, `REQUIREMENTS.md` v0.12, and
`ARCHITECTURE.md` v0.9 — all **Approved by the user on 2026-10-22** — plus
`specs/STORE_FRONT_ROUTE_COVERAGE.md` v0.2 (Draft assessment record) and
direct inspection of the current repository.

## 1. Purpose, Authority, and Boundaries

- This plan converts the approved scope, requirements, and architecture into a
  dependency-aware sequence of implementation phases. It is derived from those
  documents; it adds no scope, no requirement, and no architecture decision.
- It **does not close any open decision**. Every decision listed in
  `REQUIREMENTS.md` §6.2 (UD-001 – UD-023) and in `ARCHITECTURE.md` §12 stays
  open until the user resolves it; §6 below records which phase each one
  blocks.
- It **does not approve implementation**. Phase entry is gated on explicit
  user authorization, and each phase lists its own exit criteria.
- It **preserves the approved decisions and constraints** unchanged: the
  Vue-content-migration-before-Theme/Widget-Zone-completion rule, Redis and
  Celery retention for V1 with operational validation before production
  readiness is claimed, the deferred Transactional Outbox, refunds, automatic
  currency conversion, and actual SMS delivery, and the incremental
  brownfield migration approach.
- **Versioning** follows `specs/README.md` §6.5.1: a status or
  approval-lifecycle change alone does not increment a document's version; a
  meaning-changing content change does. This plan does not renumber or
  modify any approved document.
- Requirement and acceptance-criteria identifiers cited here exist in
  `REQUIREMENTS.md` v0.12. Page-level route state is tracked in
  `STORE_FRONT_ROUTE_COVERAGE.md`, which remains a Draft record.
- Verification of the current implementation is cited from the repository, not
  from this plan: a requirement is only "implemented" where repository
  evidence exists.

## 2. Baseline

| Item | State at 2026-10-22 (verified) |
| --- | --- |
| Approved baseline | `PROJECT_SCOPE.md` v0.10, `REQUIREMENTS.md` v0.12, `ARCHITECTURE.md` v0.9 — Approved 2026-10-22 |
| Brownfield code | Django 5.2 + DRF modular monolith (`src/`, 18 business apps, 59 models), plugin engine (`src/core/plugins`, 7 plugins), 2 themes + `theme_pacific`, Vue 3/Vite SPA (`src/frontend`, 9 interactive routes) |
| Tests | 802 passing (`pytest`, SQLite in-memory, eager Celery, LocMem cache); `ruff check src tests` clean; `scripts/test.ps1` / `test.sh` run the ruff gate and the suite |
| Database | `mssql-django` against **Microsoft SQL Server 2022 (RTM) 16.0.1000.6** (read-only probe 2026-10-21); the automated suite still runs on SQLite only |
| Redis / Celery | Installed and configured (`base.py`), but dev/test use LocMem cache + eager Celery; **no Redis service, worker, or Beat is present or documented**; no deployment manifests exist (G11) |
| Not implemented (no repository evidence) | Brand pages and brand logo/SEO data; customer address book; Contact Us page and inquiry storage; Vue Widget Zone registry/rendering; Vitest harness; CAPTCHA; plugin task registry; explicit per-currency prices; Vue content routes |

## 3. Phase Overview and Dependency Order

| Phase | Goal | Depends on | Gates |
| --- | --- | --- | --- |
| **P0** Baseline lock and regression protection | Record a trustworthy baseline, classify failures, keep the quality gate green; SQL Server integration validation is scheduled in P8 | — | none blocking P0 (UD-013/014 gate the P8 support claim; UD-001 gates final route naming) |
| **P1** Binding decisions | Resolve or explicitly defer the decisions later phases depend on | — | all UD-001 – UD-023 |
| **P2** Per-currency prices and payment guard (S3) | Explicit prices per currency; provider currency capability | P0, P1 (UD-015) | UD-015, UD-016 (resolved) |
| **P3** Browser auth transition (S4) | Session cookie + CSRF for browser flows; retire the `localStorage` token | P0, P1 (cookie/CSRF detail) | D8 detail, non-browser client auth |
| **P4** Vue content-route migration (S1, per route) | Migrate content routes to Vue one route at a time, Django template as interim fallback | P0, P1 (theme resolution may be prepared in parallel) | UD-001, UD-003 – UD-005 |
| **P5** New V1 capabilities | Brand pages, customer address book, dedicated Contact Us page | P0, P1 (UD-021, UD-023), P4 sequencing | UD-021, UD-023 |
| **P6** Theme system and Widget Zone completion (S2) | Theme resolution/fallback, layout variants, Vue Widget Zone registry and plugin components | **P4 and P5 page migration**, P1 (UD-002, UD-006/007) | UD-002, UD-006, UD-007 |
| **P7** Approved capability directions | Plugin scheduled tasks, application events, CAPTCHA, SMS compatibility | P1, P6 (plugin UI parts) | UD-019, UD-020, UD-021, UD-022 |
| **P8** Operational validation and production readiness | Redis/Celery validation, SQL Server version/portability, performance baseline, deployment runbook | P2 – P7 | UD-013/014, UD-018, D14 |

Critical path: **P0 → P1 → P4 → P5 → P6 → P8**, with **P2** and **P3** running
in parallel after P1 and **P7** after P1/P6. P8 is the only phase whose exit
permits a production-readiness claim.

## 4. Phases

### P0 — Baseline lock and regression protection (ARCHITECTURE S0)

**Goal.** Establish a trustworthy, recorded baseline **before** any behavior
change (M7) so that later work can distinguish its own regressions from
pre-existing conditions, **without** making the whole program depend on
resolving every pre-existing issue first.

**Entry criteria, dependencies, and prerequisites.** Approved baseline
documents (satisfied). No dependency on any other phase.

**Staged activities.** P0 is deliberately staged; each activity is safe to
complete independently, and later activities do not block the first.

| Activity | Content | Blocking? | Status (2026-10-22) |
| --- | --- | --- | --- |
| **P0.1** Baseline measurement | Run the suite, lint, Django system check, and migration-consistency check in the repository's documented configuration; record results, failures, skips, and environment limitations (§4.1) | No — always available | **Complete** — results in §4.1 |
| **P0.2** Failure classification | Classify every observed failure as pre-existing, environmental, or regression-introduced; a **newly introduced regression blocks the increment that caused it**, pre-existing and environmental conditions are recorded and carried forward | No | **Complete** — no failures observed; seven conditions classified and carried forward (§4.1) |
| **P0.3** Gate maintenance | Keep the ruff quality gate and the verification entry point (`scripts/test.ps1`, `scripts/test.sh`) working; add the migration-consistency check to that entry point once the baseline is green | No | **Partially complete** — the existing gate is verified green; adding the migration-consistency check to the two scripts is a script change that this task does not permit (see the status block below) |
| **P0.4** SQL Server and environment readiness | Document the current SQL Server support and test gaps, the required environment for integration validation, and the gap list for Redis/Celery (D7); **schedule** the actual SQL Server integration validation in P8 rather than requiring it here | No — explicitly deferred to P8 | **Complete** — gap list, required environment, and the P8 schedule are recorded in §4.1; no validation is claimed |

**Deliverables.**
1. A recorded baseline: commands, results, failure classification, skips, and
   environment limitations (§4.1).
2. The ruff quality gate and the verification entry point kept green, with the
   migration-consistency check added to it.
3. A written gap list for SQL Server support and testing (P0.4), naming the
   environment required and the phase in which integration validation runs.
4. The route coverage record kept current for every later cutover.

**Traceability.** NFR-TEST-001, AC-TEST-001, TR-DB-004, TR-DB-006, AC-DB-001,
AC-DB-004, AC-DB-006, FR-THEME-LAYOUT-010, AC-THEME-LAYOUT-012.

**Reuse.** The existing 802-test suite, `config/settings/test.py`,
`scripts/test.*`, and the verified fresh-database bootstrap fix.

**Migration and test strategy.** P0 changes no application behavior. Its
checks are read-only apart from creating a scratch test database outside the
repository. SQL Server work must never target the development or production
database.

**Exit criteria (progress is allowed with documented pre-existing issues).**
1. The suite has been executed in the documented configuration and the result
   is recorded, including failures, skips, and environment limitations (§4.1).
2. Every observed failure is classified as pre-existing, environmental, or
   regression-introduced, and any regression-introduced failure is fixed
   before the increment that caused it is accepted.
3. The lint gate and the verification entry point are green, and the
   migration-consistency check is part of that entry point.
4. The SQL Server support/test gap list and the required validation
   environment are written down, with the integration validation scheduled in
   P8.
5. No claim of SQL Server support, version validation, or portability is made
   from a connection or a read-only query.
6. The coverage record reflects the routes that exist today.

**Open decisions that must be resolved first.** None for P0. UD-013/014 gate
the SQL Server support claim in **P8**, and UD-001 gates final route naming
(interim names may be used meanwhile); neither blocks P0.1 – P0.4.

**P0 activity status (2026-10-22).**

- **P0.1 — complete.** Baseline recorded in §4.1: 802 tests passed, Ruff
  passed, Django system checks passed, SQLite migration consistency passed.
- **P0.2 — complete.** The suite produced **no failures, errors, or skips**,
  so there is nothing to classify as a failure. The seven observed
  **environment limitations and coverage gaps** are classified in §4.1 and
  each is carried to the phase that owns it. Pre-existing implementation gaps
  relative to the approved documents are already classified in
  `ARCHITECTURE.md` §5 (G1 – G14) and `STORE_FRONT_ROUTE_COVERAGE.md` §7
  (G-1 – G-11), and each carries a phase in §6 below. The standing rule is
  recorded: a **newly introduced regression blocks only the increment that
  caused it**, and must be fixed before that increment is accepted.
- **P0.3 — partially complete.** *Done and verified:* the quality gate and
  the verification entry point are in place and green — `scripts/test.ps1`
  and `scripts/test.sh` both run `ruff check src tests` and then `pytest`,
  and both were exercised in the documented configuration (Ruff exit 0; 802
  tests passed). *Not done:* adding the migration-consistency check to those
  two scripts. That step modifies `scripts/test.ps1` and `scripts/test.sh`,
  which this task explicitly excludes, so it is **not** claimed as done.
  *Reproducible next step (needs separate authorization):* add
  `python -m makemigrations --check --dry-run` to both scripts ahead of the
  pytest invocation and propagate its exit code the way the ruff gate does;
  verify it exits 0 with "No changes detected" under the test settings and
  non-zero when a model change is pending. The check needs a configured
  database connection and must never target a development or production
  database.
- **P0.4 — complete.** The SQL Server support and test gaps, the required
  environment for integration validation, the Redis/Celery (D7) gap list, and
  the schedule for the actual validation are written down in §4.1, with the
  validation itself scheduled in **P8** before production readiness is
  claimed. **No SQL Server compatibility, portability, or Redis/Celery
  operational validation is claimed.**

**P0 overall status.** Five of the six exit criteria above are met
(1, 2, 4, 5, 6). Criterion 3 is met in part: the lint gate and the
verification entry point are green, but the migration-consistency check is
not yet part of that entry point. **P0 is therefore not fully exited**, and
no P0 exit criterion is claimed as satisfied beyond the evidence above.

**Remaining blockers.**
1. Add the migration-consistency check to `scripts/test.ps1` and
   `scripts/test.sh` — a script change requiring separate authorization
   (P0.3).
2. SQL Server integration validation — scheduled in **P8** with
   UD-013/014; no support, version, or portability claim may be made before
   it runs (§4.1).
3. Redis/Celery runtime validation — scheduled in **P8** (D7); required
   before production readiness is claimed.

### 4.1 P0 baseline measurement (2026-10-22)

Executed in the repository's documented configuration
(`pyproject.toml` → `DJANGO_SETTINGS_MODULE = config.settings.test`,
`testpaths = ["tests"]`; entry point `scripts/test.ps1` / `scripts/test.sh`).

| # | Command (run from the repository root) | Result | Notes |
| --- | --- | --- | --- |
| 1 | `.venv\Scripts\python.exe -m pytest -ra` | **802 passed in 38.59 s** — 0 failed, 0 skipped, 0 xfailed, 0 errors | Test configuration: SQLite **in-memory**, LocMem cache, locmem email, `CELERY_TASK_ALWAYS_EAGER = True` (`config/settings/test.py`). No Redis, broker, or worker is involved |
| 2 | `.venv\Scripts\python.exe -m ruff check src tests --output-format=concise` | **All checks passed** (exit 0) | Configuration: `line-length = 120`, `target-version = "py310"`, `select = ["E","F","W","I","B"]`, `ignore = ["F403","F405"]`, `extend-exclude = ["**/migrations/*"]` |
| 3 | `.venv\Scripts\python.exe src\manage.py check` | **System check identified no issues (0 silenced)** (exit 0) | Runs with the development settings, therefore against the configured SQL Server instance |
| 4 | `migrate` then `makemigrations --check --dry-run` on a throwaway SQLite file outside the repository | migrate exit 0; **"No changes detected"** (exit 0) | Model and migration state are consistent; no pending migrations |
| 5 | Read-only `SELECT @@VERSION` through the Django connection (development settings) | `Microsoft SQL Server 2022 (RTM) - 16.0.1000.6 (X64)`; engine `mssql`; ODBC Driver 17 | **A connection and a read-only query are not validation** and are not treated as such (see the gap list below) |

**Failure classification (P0.2).** The suite produced **no test failure, no
error, and no skip**, so there is nothing to classify as a failure and no
regression was introduced. The conditions below are **environment limitations
and coverage gaps**, not test failures; each is classified and carried forward
as shown. Pre-existing implementation gaps relative to the approved
documents are classified separately in `ARCHITECTURE.md` §5 (G1 – G14) and
`STORE_FRONT_ROUTE_COVERAGE.md` §7 (G-1 – G-11), and each carries a phase in
§6 below. The standing rule applies to all later increments: a newly
introduced regression blocks only the increment that caused it and must be
fixed before that increment is accepted; pre-existing and environmental
conditions are recorded and carried forward.

| Gap / limitation | Evidence | Classification | Carried to |
| --- | --- | --- | --- |
| The suite never exercises SQL Server; it runs on SQLite in-memory | `config/settings/test.py:23-28` pins the engine to `sqlite3`; no settings switch exists to run the suite against SQL Server | Coverage gap — SQL Server behavior is untested | P8 (and a settings change is a prerequisite of it) |
| SQL Server version support is unvalidated | `ARCHITECTURE.md` §2.1 and UD-013; a successful connection and `SELECT 1` say nothing about migration execution, backend-specific query behavior, or version support | Open decision, not a defect | P8 / UD-013, UD-014 |
| Database portability is unverified | TR-DB-006 requires repeatable checks that detect backend-specific queries and migration incompatibilities; no such check exists | Open decision, not a defect | P8 / UD-014 |
| Redis and Celery are not exercised at all: no Redis server or `redis-cli` is installed, nothing listens on 6379, no worker or Beat is present, and the dev/test configuration uses LocMem cache plus eager Celery | `config/settings/development.py:13-19`, `config/settings/test.py:30-34, 43-45`; environment probes on 2026-10-22 | Environment limitation — D7 operational validation cannot run in this environment | P8 (D7) |
| No CI configuration exists in the repository (no workflow or pipeline files) | Repository scan on 2026-10-22 | Coverage gap — the lint gate and the suite run only locally | P8 |
| The built SPA output is git-ignored, so a fresh clone has no SPA build and the Vue rendering path is not covered by the Python suite | `.gitignore`, `src/frontend/vite.config.js` | Environment limitation | P4 (Vue migration) and P6 (Vitest) |
| Celery's prefork pool is unavailable on Windows, so any worker validation must use the solo pool | Environment fact recorded during D7 preparation | Environment limitation | P8 (D7) |

**Required environment for SQL Server integration validation (P8).** A scratch
SQL Server database (never the development or production database);
`mssql-django` with the ODBC Driver; a documented way to point the test
configuration at that database, which today requires a settings change because
`config/settings/test.py` hard-codes SQLite; and the suite executed with
`DATABASE_URL` set accordingly. The validation must then cover: full
migration application on SQL Server, the full suite, migration reversibility
where practical, and the portability checks required by TR-DB-006.

**Current status of P0.** P0.1, P0.2, and P0.4 are complete against the
evidence recorded above; **P0.3 is partially complete** — the lint gate and
the verification entry point are verified green, but the migration-consistency
check is not yet part of that entry point, and adding it requires a change to
`scripts/test.ps1` and `scripts/test.sh` that this task does not permit. Five
of the six P0 exit criteria are met; **P0 is not fully exited**, no P0 exit
criterion is claimed beyond that evidence, and no phase has been entered.
The full status, the evidence behind it, and the remaining blockers are in
§4 ("P0 activity status"). SQL Server integration validation and
Redis/Celery runtime validation remain scheduled in **P8**, before production
readiness is claimed.

### P1 — Binding decisions (design gate)

**Goal.** Convert the open decisions that later phases depend on into recorded
outcomes, so no phase starts on an unresolved assumption.

**Deliverables.** One decision record per resolved item under
`specs/decisions/`; corresponding updates to `REQUIREMENTS.md` §6.2/§6.3 and
`ARCHITECTURE.md` §12 **only when the user resolves them**; explicit
deferral records for items not resolved, naming the phase that inherits them.

**Traceability.** UD-001 – UD-023 (each mapped in §6 below), plus the
architecture open items in `ARCHITECTURE.md` §12 (cookie/CSRF detail,
non-browser client authentication, serving arrangement, `apps.shipping`
disposition, dormant refund/return model disposition).

**Exit criteria.** Every open decision is either resolved by explicit user
approval or explicitly deferred to a named phase. No decision is closed by
inference, and no new identifier is allocated without the user's approval.

### P2 — Per-currency price storage and payment-currency guard (ARCHITECTURE S3)

**Goal.** Store an explicit price per supported currency and refuse a payment
provider that does not support the order currency.

**Entry criteria, dependencies, and prerequisites.** P0 exit; UD-015 resolved (storage and resolution design).

**Deliverables.** Explicit per-currency price storage with a defined
resolution when no explicit price exists; payment-method currency capability;
checkout/order guard; store-settings and discount behavior carried across
currencies.

**Traceability.** FR-CUR-001 – FR-CUR-008, AC-CUR-001 – AC-CUR-009, FR-PAY-001 –
FR-PAY-002, AC-PAY-001 – AC-PAY-003, FR-DISC-001, AC-DISC-001, FR-SET-001,
AC-SET-001, TR-DB-005, AC-DB-005.

**Reuse.** Existing catalog/pricing models, the checkout pipeline, the
existing settings service for the base currency.

**Migration and test strategy.** Additive price rows plus a validated,
re-runnable data migration (TR-DB-005); the current base-currency price
remains the effective price until an explicit price exists, so no rewrite of
the cart or checkout flow is required. Tests cover price resolution, the
payment-currency guard, and discount/tax behavior per currency.

**Exit criteria.** AC-CUR-001 – AC-CUR-009 and AC-PAY-001 – AC-PAY-003 pass;
refund behavior stays untouched (UD-017 deferral preserved); the migration is
reversible or its recovery approach documented.

### P3 — Browser auth transition (ARCHITECTURE S4)

**Goal.** Move browser flows to the same-origin session cookie + CSRF model
used by the Django Admin, retiring the browser `localStorage` token.

**Entry criteria, dependencies, and prerequisites.** P0 exit; cookie/CSRF integration detail designed
(ARCHITECTURE §12 open item); non-browser client authentication decision
recorded (the API token flow is retained for non-browser clients unless the
user decides otherwise).

**Deliverables.** Session-cookie authentication and CSRF enforcement for
browser routes and the storefront API as used by the browser; documented
cutover of the browser token flow; the non-browser client path unchanged
unless separately decided.

**Traceability.** D8, G5, FR-CUST-001, AC-CUST-001, NFR-SEC-001, AC-SEC-001,
FR-ADMIN-001 – FR-ADMIN-003, AC-ADMIN-001 – AC-ADMIN-003, AC-CUST-002
(address ownership continues to hold).

**Reuse.** Django Admin's session model, the existing identity backend
(`apps/identity`), and the existing brute-force/throttle cache integration.

**Migration and test strategy.** Coexistence window: the session path ships
first, the browser token path is retired only after the session path passes
its acceptance criteria and no browser code path still reads the token.
Tests cover CSRF rejection, session expiry, brute-force counters through the
cache, and the existing authentication suite unchanged.

**Exit criteria.** Browser flows are session-based; CSRF is enforced; no
`localStorage` token remains in browser code paths; the authentication and
security suites are green.

### P4 — Vue content-route migration (ARCHITECTURE S1, per route)

**Goal.** Migrate the content routes to the Vue storefront one route at a
time, which is the precondition for completing the Theme and Widget Zone
system (CF-010, `PROJECT_SCOPE.md` §6.5).

**Entry criteria, dependencies, and prerequisites.** P0 exit; per-route acceptance criteria identified;
`UD-003` – `UD-005` theme resolution may be prepared in parallel but is not
required to start a route migration.

**Deliverables (per route).** A Vue page component consuming the existing
DRF endpoints; the route's acceptance criteria green; the Django template
retained as an interim fallback until the cutover passes; the route's row in
`STORE_FRONT_ROUTE_COVERAGE.md` updated (implementation, theme integration,
zones, tests, migration state). Suggested order: home → category listing →
product detail → search results → blog list/detail → informational/CMS page.

**Traceability.** FR-THEME-LAYOUT-001, FR-THEME-LAYOUT-004, AC-THEME-LAYOUT-001 –
AC-THEME-LAYOUT-015, TR-STACK-003, TR-STACK-006, AC-API-001, FR-EXT-001,
M5 (temporary ≠ target), M7 (regression protection), AC-THEME-LAYOUT-012.

**Reuse.** The existing DRF API surface (`config/api_urls.py`), the SPA shell
(`App.vue`), `SiteHeader`/`SiteFooter`, the SPA store and API client, and the
existing Django templates as interim fallbacks.

**Migration and test strategy.** No big-bang switch: a route is cut over only
after its own acceptance criteria pass, and the Django template is retired
per route, not globally. The existing Django route tests stay green
throughout (they cover the fallback), and Vitest component tests are added
alongside them. `STORE_FRONT_ROUTE_COVERAGE.md` is the per-route ledger of
migration state and is updated in the same change as each cutover.

**Exit criteria.** Every content route in the coverage record is Vue-served
with its acceptance criteria met and its coverage row updated; no content
route remains served only by a Django template; the interim fallbacks are
retired route by route.

**Progress (2026-10-22).** The **first migrated content route** is delivered:
the brand listing and brand detail pages (`FR-CAT-006`, `FR-CAT-007`,
`AC-CAT-006`, `AC-CAT-007`) are Vue SPA routes (`BrandListView.vue`,
`BrandDetailView.vue`, shared `BrandLogo.vue` and `seo.js` composable) served
through the existing `spa_page(...)` mechanism with a server-rendered Django
fallback, and their rows in `STORE_FRONT_ROUTE_COVERAGE.md` record the
implemented state. Remaining for these routes: Widget Zone rendering and its
Vitest verification (`FR-EXT-001`, `AC-ZONE-003`), a theme-specific page
component (`UD-003` – `UD-005`), and Vue component tests — the frontend still
has no test runner, so the smallest follow-up is adding Vitest with focused
component tests. The other content routes (home, category, product, search,
blog, CMS) are not migrated and remain server-rendered.

**Progress (2026-10-22, second increment).** The **category route is migrated**
to the Vue storefront (`CategoryView.vue`, router entry `/category/:slug/`),
served through the existing `spa_page(...)` mechanism with the
server-rendered `storefront/category.html` retained as the fallback; an
inactive or unknown category renders the "not available" state, matching the
fallback's 404 behavior. The **Vitest component-test harness** now exists in
`src/frontend` (`vitest`, `@vue/test-utils`, `jsdom`; `npm test` → `vitest
run`; `environment: 'jsdom'` in `vite.config.js`), with focused specs for
the brand list, brand detail and category views covering loading, error,
empty, not-found/unavailable and missing-logo behavior. Navigation stays
CMS-driven — a `MenuItem` with `url = /category/<slug>/` makes the page
reachable from the shared header. Remaining for these routes: Widget Zone
rendering and its Vitest verification (`FR-EXT-001`, `AC-ZONE-003`), a
theme-specific page component (`UD-003` – `UD-005`), and product, search,
blog and CMS migration.

**Progress (2026-10-22, third increment).** The **product detail route is
migrated** to the Vue storefront (`ProductDetailView.vue`, router entry
`/product/:slug/`), served through the existing `spa_page(...)` mechanism with
the server-rendered `storefront/product_detail.html` retained as the
fallback. The page renders the product name, description, images (with an
initial fallback when a product has none), price, compare-at price, SKU,
availability, brand/category links and the attribute options, and it adds the
selected product or variant to the cart through the existing cart API
(`FR-CAT-002`, `FR-CAT-003`, `FR-CAT-004`). Selecting a variant or an option
combination updates the displayed price, SKU and availability, and a
combination that no variant carries is refused in the page; the cart API
revalidates the selection and now also rejects an inactive variant. The
catalog product endpoint exposes the product record only, so the page reads
the new storefront endpoint `/api/v1/storefront/products/<slug>`, which
assembles the images, variants, option groups, price and availability from the
existing models and services. The reusable `ProductMedia.vue` component backs
the product gallery and the product cards of the brand and category pages,
whose product links now stay inside the SPA. Covered by a new Vitest spec
(`ProductDetailView.spec.js`, 13 tests) and by
`tests/test_api/test_product_detail_api.py` (10 tests). Not implementable
without a model change, and reported as such: a variant-specific image
(`ProductVariant` has no image field) and an explicit per-currency price
(`Product` has a single `price`; see `STORE_FRONT_ROUTE_COVERAGE.md` gap
G-12). Remaining for this route: Widget Zone rendering and its Vitest
verification (`FR-EXT-001`, `AC-ZONE-003`) and a theme-specific page component
(`UD-003` – `UD-005`); home, search, blog and CMS migration is still
outstanding.

### P5 — New V1 capabilities: brand pages, address book, Contact Us

**Goal.** Deliver the three capabilities approved on 2026-10-22, built as
Vue pages so they participate directly in the P4 migration model.

**Entry criteria, dependencies, and prerequisites.** P0 exit; UD-023 (contact inquiry administration,
retention, recipient/channel configuration) resolved for the parts that affect
the page and the stored record; UD-021 resolved for the CAPTCHA aspect of the
contact form.

**Deliverables.**
- **Brand (FR-CAT-006, FR-CAT-007):** brand listing and brand detail pages;
  brand name, description, logo, and SEO metadata; public brand surfaces
  expose active brands only.
- **Address book (FR-CUST-002, FR-CHK-001):** a reusable customer-owned
  address entity — **distinct from the order address snapshot** — with
  customer-only modification, an optional default address, staff read-only
  access in Django Admin, checkout selection of an owned address, and the
  selected address copied into the order snapshot.
- **Contact Us (FR-CONTACT-001):** a dedicated route and page, server-side
  validation with clear feedback, stored inquiry, and a notification sent
  through the existing notification capabilities.

**Traceability.** FR-CAT-006, FR-CAT-007, AC-CAT-006, AC-CAT-007, FR-CUST-001,
FR-CUST-002, AC-CUST-001, AC-CUST-002, FR-CHK-001, AC-CHK-001, AC-CHK-002,
FR-CONTACT-001, AC-CONTACT-001, FR-NOTIF-001, AC-NOTIF-001, TR-DB-004,
TR-DB-005.

**Reuse.** The `Brand` model and `BrandViewSet` (slug lookup, search,
ordering) and the existing `?brand=<slug>` product filter; the existing
notification providers, `NotificationMessage` rows and `queue_notification`;
the existing Django Admin registration model; the existing checkout pipeline
and order snapshot model.

**Migration and test strategy.** All three introduce new persisted entities
or fields, so versioned migrations plus validated data migrations are
required (TR-DB-004, TR-DB-005). The address book must prove ownership
isolation (one customer's address is never readable or writable by another)
and snapshot immutability (changing or deleting a saved address never alters
an existing order). The contact form must prove validation, storage,
notification delivery, and the no-inquiry-on-invalid-input rule; notification
delivery is tested against stub or in-memory providers, never a live channel.

**Exit criteria.** AC-CAT-006/007, AC-CUST-002, AC-CHK-002, AC-CONTACT-001
pass; inactive brands are not exposed publicly; address ownership and order
snapshot immutability are proven by tests; the coverage record lists all four
new routes as required-and-implemented with their zone state recorded.

**Progress (2026-10-22).** The **address-book** part of P5 is implemented and
tested, delivered through the API-first backend (TR-STACK-002): the
customer-owned `Address` entity (`apps/identity/models.py`, migration
`identity.0003_address`) distinct from the order address snapshot; the
address-book rules in `apps/identity/services/addresses.py` (ownership and the
single-default invariant); the customer-scoped API
`/api/v1/customers/me/addresses`; checkout selection of an **owned** saved
address copied into the order snapshot (`FR-CHK-001`); and the read-only staff
registration in Django Admin. Covered by `FR-CUST-002`, `FR-CHK-001`,
`AC-CUST-002`, `AC-CHK-002`; the storefront UI for the address book, the brand
pages, and the Contact Us page remain outstanding — the storefront surface
follows the Vue migration and the Vitest harness (P4/P6), and the Contact Us
page still depends on UD-021/UD-023.

**Progress (2026-10-22, second increment).** The **brand data and public
visibility** part of P5 is implemented and tested: brand logo and SEO metadata
(`FR-CAT-007`, migration `catalog.0003_brand_canonical_url_brand_logo_and_more`),
the shared `SEOMixin` moved to the core kernel and reused by both CMS content
and catalog brands, the SEO fallback to the brand name and description, and
public brand list/retrieve responses restricted to active brands (the
`FR-CAT-006` exposure clause) while staff holding `catalog.brand.manage`
retain full visibility. The brand **listing and detail pages** are not
implemented in this increment and remain part of the Vue content-route
migration.

### P6 — Theme system and Widget Zone completion (ARCHITECTURE S2)

**Goal.** Complete the Theme system and the Widget Zone system on top of the
migrated Vue storefront.

**Entry criteria (hard).** The relevant content pages have migrated to Vue
(P4) and the new pages from P5 are Vue-served. Completion of the Theme and
Widget Zone system must follow that migration (CF-010, `PROJECT_SCOPE.md`
§6.5). Preliminary theme/zone groundwork before the migration is allowed but
does not satisfy this entry criterion.

**Deliverables.** Theme package resolution with deterministic fallback and
layout variants; administratively authorized theme activation and
configuration; the Widget Zone registry and the plugin Vue component contract;
theme-aware plugin components; actual zone rendering on the routes that
declare zones, with the documented empty/fallback state when no plugin
contributes.

**Traceability.** FR-THEME-001, FR-THEME-002, AC-THEME-001, AC-THEME-002,
FR-THEME-LAYOUT-001 – FR-THEME-LAYOUT-012, AC-THEME-LAYOUT-001 –
AC-THEME-LAYOUT-015, FR-EXT-001 – FR-EXT-004, AC-EXT-001 – AC-EXT-003,
AC-ZONE-001 – AC-ZONE-003, NFR-EXT-001, NFR-TEST-001.

**Reuse.** The existing plugin engine (`core/plugins`), the theme package
mechanism and `SEOMixin` SEO pattern, the SPA shell, and the existing
server-rendered hook fragments — retained only as the interim mechanism for a
zone that is not yet migrated, and retired zone by zone.

**Migration and test strategy.** The **Vitest** harness must exist before the
first zone is cut over: AC-ZONE-003 requires an automated test per route that
asserts zone rendering, a plugin contribution, and the no-contribution
fallback. The server-rendered fragment path stays in place until each zone's
Vue rendering passes, so no capability regresses during the switch. The
coverage record is the acceptance ledger: every route must be classified with
its page type, page component, root layout, shared components, layout
variant, and zones, and no route may be left unclassified (AC-THEME-LAYOUT-012).

**Exit criteria.** AC-THEME-LAYOUT-012 is satisfied; every route that
declares a zone renders it with plugin contribution and fallback verified by
Vitest; theme activation is administratively authorized and persistent; the
coverage record's zone columns reflect actual rendering.

### P7 — Approved capability directions: scheduled tasks, events, CAPTCHA, SMS

**Goal.** Deliver the four capability directions approved for V1.

**Entry criteria, dependencies, and prerequisites.** P1 outcomes for UD-019, UD-020, UD-021 and the deferred
part of UD-022; P6 for the plugin-facing UI parts.

**Deliverables.** Plugin-declared scheduled tasks with administration and
overlap policy; a documented event catalog with per-event delivery
classification; server-side CAPTCHA verification with a provider boundary
and secure credential handling; an SMS provider boundary that preserves
existing registration and authentication behavior.

**Traceability.** FR-PLUG-001, FR-PLUG-002, AC-PLUG-001, AC-PLUG-002,
FR-EVT-001 – FR-EVT-004, AC-EVT-001 – AC-EVT-003, FR-CAPTCHA-001 –
FR-CAPTCHA-006, AC-CAPTCHA-001 – AC-CAPTCHA-004, FR-SMS-001 – FR-SMS-005,
AC-SMS-001, AC-SMS-002, NFR-REL-001, AC-REL-001.

**Reuse.** `core/jobs` (`job_task` decorator, retry/backoff/logging),
`core/events` (typed dispatcher, registry, async task), the existing
`CELERY_BEAT_SCHEDULE` hook, the existing settings/credentials mechanism, and
the existing notification sweep tasks.

**Migration and test strategy.** The V1 event-consistency limits of
`ARCHITECTURE.md` §10.5.2 apply: an enqueue failure must not invalidate an
otherwise successful committed transaction, failures are logged with context
and alerted, recovery is event-specific and best-effort, and **no delivery
guarantee, exactly-once handling, or automatic replay is promised**. The
**Transactional Outbox and any equivalent durable event-recovery mechanism are
deferred to a future release and must not be introduced in V1**. Tests cover
enqueue-failure behavior, retry/backoff, CAPTCHA verification, and unchanged
registration flows.

**Exit criteria.** AC-PLUG-002, AC-EVT-001 – AC-EVT-003, AC-CAPTCHA-001 –
AC-CAPTCHA-004, AC-SMS-001/002 pass; the notification sweep tasks have a
registered schedule; no Outbox-like mechanism exists in the codebase.

### P8 — Operational validation and production readiness (ARCHITECTURE S5)

**Goal.** Produce the evidence that the approved architecture works in
operation, so a production-readiness claim can be made — and not before.

**Entry criteria, dependencies, and prerequisites.** P2 – P7 delivered and their exit criteria met.

**Deliverables.**
1. **Redis/Celery operational validation** (D7): static configuration
   evidence; a running Redis with cache round-trip, key-isolation and
   health-endpoint evidence; broker connectivity, worker execution and result
   backend evidence; induced-outage evidence for the decided failure and
   degradation behaviors (login availability, API availability under cache
   outage, order-commit safety when enqueueing fails, search-index recovery,
   health degradation signaling). Any service installation, worker start, or
   outage induction requires explicit user approval and must use an isolated
   Redis instance and a scratch database.
2. **SQL Server support and portability validation** (UD-013, UD-014,
   TR-DB-001, TR-DB-006): minimum supported version recorded; repeatable
   portability checks; no configuration-only database-switch claim.
3. **Performance baseline** (UD-018, NFR-PERF-001 – NFR-PERF-003,
   AC-PERF-001 – AC-PERF-003): the documented baseline load test and the LCP
   measurement, on realistic data volumes.
4. **Deployment and operability**: the serving topology under D14, worker and
   Beat health observability, and an operator runbook for Redis, the worker
   and Beat (G11).

**Traceability.** D7, UD-013, UD-014, UD-018, TR-DB-001, TR-DB-006, AC-DB-001,
AC-DB-006, NFR-PERF-001 – NFR-PERF-003, AC-PERF-001 – AC-PERF-003, NFR-REL-001,
D14, G11.

**Exit criteria.** Validation evidence is recorded for every item above;
**production readiness may be claimed only after the Redis/Celery operational
validation evidence exists**; the outstanding risk and the evidence
requirement remain visible until then.

## 5. Existing Functionality to Reuse (Brownfield)

- **Backend foundation:** Django apps, `BaseModel` conventions, DRF API
  surface, `core` kernel (plugins, events, cache, security, settings, audit,
  jobs), provider interfaces for payment, shipping, and notifications.
- **Commerce flow:** cart, checkout pipeline with plugin-extensible steps,
  order state machine, order/address snapshot models, discount engine,
  inventory, reviews, CMS, media, search.
- **Storefront:** Django storefront templates and views (interim fallback),
  the Vue SPA shell and its nine interactive routes, `SiteHeader`/`SiteFooter`,
  the SPA store and API client.
- **Platform:** the plugin engine and its 7 plugins, the theme package
  mechanism and `SEOMixin` SEO pattern, the multilingual/RTL foundation, the
  Django Admin (`admin_panel`, `core.audit`), and the 802-test regression
  suite with the ruff quality gate.
- **Incremental over replacement:** every phase above extends the existing
  system and keeps the current path working until the new path passes its
  acceptance criteria; no phase assumes the brownfield code is wrong merely
  because it differs from the target.

## 6. Open Decisions That Gate Work

| Decision | Subject | Blocks |
| --- | --- | --- |
| UD-001 | Route classification and migration mapping | P0 (final route naming), P4, P5 |
| UD-002 | Theme activation persistence and invalidation | P6 |
| UD-003 – UD-005 | Theme resolution contract, package layout, layout variants | P4 (partial, parallel), P6 |
| UD-006 – UD-007 | Plugin Vue component contract; Widget Zone registry and ordering | P6, P7 (plugin UI) |
| UD-008 | Reserved — not to be allocated | — |
| UD-010 | Translation fallback and content localization | P4 for content pages (fallback behavior) |
| UD-011 | Theme/plugin trust and security model | P6 (installation path) |
| UD-013 / UD-014 | SQL Server version validation; portability checks | P8 (P0.4 records the gap only) |
| UD-015 | Per-currency price storage and resolution | P2 |
| UD-018 | Performance test environment, tooling, workload | P8 |
| UD-019 | Scheduled-task administration and overlap policy | P7 |
| UD-020 | Event catalog, publication boundaries, delivery guarantees | P7 |
| UD-021 | CAPTCHA form policy, provider type/version, failure policy | P5 (contact form), P7 |
| UD-022 | SMS policy details (release assignment resolved; delivery deferred) | P7 (deferred part) |
| UD-023 | Contact inquiry administration, retention, notification recipient/channel configuration | P5 |
| ARCHITECTURE §12 | Cookie/CSRF detail; non-browser client authentication; serving arrangement; `apps.shipping` disposition; dormant refund/return model disposition | P3, P8, P2 (refund models) |
| D7 | Redis/Celery operational validation (retention decided) | P8 exit — production-readiness claim only |

## 7. Sequencing Constraints That Must Be Preserved

1. **Content pages migrate to Vue before the Theme and Widget Zone system is
   completed** (CF-010, `PROJECT_SCOPE.md` §6.5, `REQUIREMENTS.md` §1.13).
   Preliminary groundwork is allowed; completion follows the migration.
2. **Redis and Celery are retained for V1, and their operational validation
   must be complete before production readiness is claimed** (D7, resolved
   2026-10-22; `ARCHITECTURE.md` §10.3/§10.5/§12). No validation has been
   performed, and the outstanding risk and evidence requirement remain
   visible.
3. **Per-route cutover with a temporary fallback** — the Django template is a
   transitional mechanism, retired route by route (M5, M7).
4. **No Transactional Outbox or equivalent durable event-recovery mechanism in
   V1** (`ARCHITECTURE.md` §10.5.2).
5. **Deferred scope stays deferred:** refunds and automatic currency
   conversion (UD-017, UD-009), SMS delivery and phone-number verification
   (UD-022), Vue control of the administration interface (V1 Django Admin),
   and PostgreSQL as a configuration-only switch (TR-DB-006).
6. **One-origin deployment** for SPA, API, and Admin (D14).
7. **No open decision is closed by implementation** — a decision changes only
   by explicit user approval.

## 8. Test Strategy (Applies to Every Phase)

- The existing 802-test suite plus the ruff gate are the regression baseline;
  no phase may reduce coverage.
- Acceptance criteria for the increment are the gate: a phase step ships only
  when its acceptance criteria pass, and the Django fallback stays until they
  do.
- **Vitest** is the approved framework for Vue component and Widget Zone
  tests (NFR-TEST-001, AC-ZONE-003); the harness is a prerequisite of P6, not
  an optional extra.
- **SQL Server parity:** every schema-changing phase runs the suite against
  SQL Server on a scratch database in addition to SQLite.
- **Authorization isolation** is tested explicitly for the address book
  (AC-CUST-002) and for any new staff-facing surface.
- **Migration discipline:** versioned, validated, re-runnable where practical,
  with rollback or a documented recovery approach (TR-DB-004, TR-DB-005,
  AC-DB-004, AC-DB-005).
- **Notification and event tests** use stub or in-memory providers; no test
  may send a real email, call a real webhook endpoint, or enqueue onto a
  shared production broker.
- **Performance** is measured against the documented baseline (UD-018) before
  performance targets are claimed.

## 9. Phase Status

| Phase | Status | Entry authorized |
| --- | --- | --- |
| P0 Baseline lock | P0.1, P0.2, P0.4 complete; **P0.3 partially complete** (migration-consistency check not yet added to the scripts); 5 of 6 exit criteria met — **P0 not fully exited** (§4, §4.1) | — |
| P1 Binding decisions | Not started | — |
| P2 Per-currency prices | Not started | — |
| P3 Browser auth transition | Not started | — |
| P4 Vue content-route migration | Migrated content routes: brand listing, brand detail, category and product detail (2026-10-22, see P4 progress); home, search, blog and CMS not started | — |
| P5 New V1 capabilities | Address book implemented and tested through the API-first backend (2026-10-22, see P5 progress); brand data and public visibility implemented and tested (2026-10-22, see P5 progress); brand pages and Contact Us page not started | — |
| P6 Theme and Widget Zone completion | Not started | — |
| P7 Capability directions | Not started | — |
| P8 Operational validation and production readiness | Not started | — |

No phase is started by this document. Phase entry requires explicit user
authorization, and each phase begins with its entry criteria being verified
against the current repository state.
