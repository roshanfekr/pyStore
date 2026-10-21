# Storefront Route Coverage Record

**Document:** `specs/STORE_FRONT_ROUTE_COVERAGE.md`\
**Version:** 0.2\
**Status:** Draft — assessment record (not an approved specification)\
**Last updated:** 2026-10-22\
**Basis:** Direct inspection of the working tree at commit `88669ba` (branch `main`,
clean working tree). The assessment is read-only; no application code, test,
configuration, dependency, or database state was changed. Revision 0.2 adds
the routes and requirements approved on 2026-10-22 (brand listing and brand
detail, customer address book, dedicated Contact Us page) and the approved
Theme/Widget Zone implementation sequence; it changes no application code and
makes no implementation claim.\
**Purpose:** Evidence-based record of existing storefront route coverage, theme
integration, and plugin hook (Widget Zone precursor) integration, produced to
support `UD-001` and to establish the baseline for `FR-THEME-LAYOUT-010` /
`AC-THEME-LAYOUT-012`.

## 1. Authority and Boundaries

- This document **records existing behavior only**. It does not define a theme
  architecture, a Widget Zone registry, component-resolution rules, or a
  migration plan; those remain open decisions in `REQUIREMENTS.md` §6.2
  (`UD-002` – `UD-007`) and `ARCHITECTURE.md` §7.
- It **does not modify** `PROJECT_SCOPE.md`, `REQUIREMENTS.md`,
  `ARCHITECTURE.md`, or `specs/README.md`, and it does not change the status
  or approval state of any requirement or acceptance criterion.
- Requirement identifiers are cited only where they exist in
  `REQUIREMENTS.md` v0.11. Where a route, file, or behavior could not be
  verified from the repository, the cell reads `Not verified` or
  `Not found` instead of an assumption.
- The source code is evidence of current behavior, not proof of intended
  behavior (`specs/README.md` §5, rule 5).

## 2. Method and Evidence Base

| Evidence | Path / command |
| --- | --- |
| Root URL configuration | `src/config/urls.py` |
| API URL configuration | `src/config/api_urls.py` |
| Storefront URL configuration | `src/apps/storefront/urls.py` |
| Storefront views | `src/apps/storefront/views.py` |
| Storefront templates (19 files) | `src/apps/storefront/templates/storefront/` |
| SPA serving module | `src/apps/storefront/spa.py` |
| Storefront JSON API | `src/apps/storefront/api.py` |
| Plugin hook rendering | `src/apps/storefront/hooks.py`, `src/apps/storefront/templatetags/plugin_hooks.py` |
| Theme resolution | `src/apps/storefront/themes.py`, `src/core/plugins/theme_discovery.py`, `src/config/settings/base.py` |
| Theme packages | `src/themes/default/`, `src/themes/alt-theme/`, `src/plugins/theme_pacific/` |
| Vue SPA | `src/frontend/src/router/index.js`, `src/frontend/src/App.vue`, `src/frontend/src/views/`, `src/frontend/src/components/`, `src/frontend/src/stores/storefront.js` |
| Tests | `tests/test_storefront/`, `tests/test_api/`, `tests/test_plugins/` |

The stale git worktree at `src/.kilo/worktrees/` was excluded from all
evidence, as recorded in `ARCHITECTURE.md` §2.

## 3. Rendering Architecture as Implemented

1. **Two rendering paths coexist.** `src/apps/storefront/urls.py:29-44`
   defines `spa_page()`, which serves the built Vue SPA for a route when
   `STOREFRONT_SPA_ENABLED` is true (`src/config/settings/base.py:259`,
   default `False`; `.env.example` sets `True` for development) and otherwise
   renders the Django view. Content routes are always server-rendered.
2. **A plugin may take over a route.** `spa_page(view, hook=...)` checks
   `_plugin_claims(hook)`; the `cart` route declares `hook="cart_page"`, which
   `ajax_cart` registers, so that route is server-rendered even when the SPA is
   enabled (`src/apps/storefront/urls.py:10-26, 58`).
3. **The SPA build is not tracked by git.** `src/apps/storefront/static/storefront-spa/`
   is git-ignored (`.gitignore`); `src/frontend/vite.config.js` emits the
   build there. A fresh clone has no build, and `spa_index()` then returns a
   503 "storefront SPA not built" page (`src/apps/storefront/spa.py:14-37`).
4. **Themes are Django template packages.** The active theme is resolved from
   the `ACTIVE_THEME` setting (`src/apps/storefront/themes.py:9-10`), and its
   `templates/` and `static/` directories are injected into the template and
   static search paths (`src/config/settings/base.py:80-102`). Built-in themes
   in `src/themes/<slug>/` take precedence over plugin-provided themes with
   the same slug (`src/core/plugins/theme_discovery.py:47-54`).
5. **Plugin storefront contributions are server-rendered HTML fragments.**
   `render_plugin_hook()` renders each enabled plugin's template and returns
   `{"plugin_id", "html"}` (`src/apps/storefront/hooks.py:15-46`); the
   `{% plugin_hook %}` tag joins the fragments with `mark_safe`
   (`src/apps/storefront/templatetags/plugin_hooks.py:9-13`).

## 4. Route Coverage Matrix

Column meanings: **Theme integration** — whether a theme can change the
rendering of the page today; **Widget Zone integration** — the plugin hook
zones that exist at that page today; **Tests** — existing automated coverage
or `No identified coverage`; **Status / gaps** — evidence-based findings and
remaining work. All route patterns are quoted from
`src/apps/storefront/urls.py` unless stated otherwise.

### 4.1 Home

| Route / URL pattern | Page / user journey | Implementation | Template / component | Theme integration | Widget Zone integration | Tests | Status / gaps | Traceability |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `""` (name `home`) | Storefront landing page, newest 12 published products | Django view `home_view` (`views.py:71-78`) | `storefront/home.html` extends `storefront/base.html` | Existing — Django template override (`theme_pacific` ships its own `home.html`); theme CSS is **not** linked by the core layout | Zones present: `home_top` (home.html:5), `home_middle` (home.html:10), `home_bottom` (home.html:28) | `tests/test_storefront/test_storefront.py` (`test_home_shows_published_products`, `test_product_card_shows_image`, `test_theme_template_override_mechanism`, `test_theme_branding_in_base`); `tests/test_storefront/test_theme_pacific.py` (`test_pacific_theme_renders_when_active`) | No Vue route exists for home; the page is server-rendered only. `slider` and `flash_sale` both contribute to `home_middle` (server-rendered fragments only) | FR-THEME-LAYOUT-001, FR-THEME-LAYOUT-010, FR-EXT-001, AC-THEME-LAYOUT-012, UD-001 |

### 4.2 Catalog: category, product, search, brands, filtering and sorting

| Route / URL pattern | Page / user journey | Implementation | Template / component | Theme integration | Widget Zone integration | Tests | Status / gaps | Traceability |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `category/<slug:slug>/` (name `category`) | Browse a category and its descendants | Django view `category_view` (`views.py:81-90`) | `storefront/category.html` extends `storefront/base.html` | Existing — Django template override; no theme ships a `category.html` override | Absent (no hook call in the template) | `tests/test_storefront/test_storefront.py` (`test_category_page_with_descendants`) | **No filtering, sorting, or paging controls** in the view or template; the view returns all category products unordered. Filtering/sorting exist only in the API viewset (`src/apps/catalog/api.py:92-94`: `ordering_fields`, `search_fields`) | FR-CAT-005, FR-THEME-LAYOUT-001, AC-CAT-005, AC-THEME-LAYOUT-012 |
| `product/<slug:slug>/` (name `product`) | Product detail with variants, price, images, availability | Django view `product_detail_view` (`views.py:160-192`) | `storefront/product_detail.html` (+ `storefront/_product_media.html` partial) extends `storefront/base.html` | Existing — Django template override (`theme_pacific` ships `product_detail.html`) | Absent (no hook call in the template) | `tests/test_storefront/test_storefront.py` (`test_product_detail_page`, `test_product_detail_shows_all_images`, `test_product_detail_rich_layout`); `tests/test_storefront/test_theme_pacific.py` (`test_pacific_product_detail_renders_gallery`) | Variant selection is server-rendered (`option` pills + `variant-select` element, product_detail.html:105-135) with a server-side revalidation on add-to-cart; no Vue route exists | FR-CAT-002/003/004, FR-THEME-LAYOUT-001, AC-CAT-002/003/004, AC-THEME-LAYOUT-012 |
| `search/` (name `search`) | Full-text product search | Django view `search_view` (`views.py:195-205`); results via `apps.search.service.search_service` | `storefront/search.html` extends `storefront/base.html` | Existing — Django template override | Absent | `tests/test_storefront/test_storefront.py` (`test_search_view`); `tests/test_search/test_search.py` (service level) | No filters/sort in the search page; SPA-side search is a separate endpoint (`/api/v1/storefront/search`) not used by any Vue view | FR-CAT-005, AC-CAT-005, FR-THEME-LAYOUT-010 |
| **Proposed route** `brands/` (path and URL name are placeholders; final route naming is an architecture decision, `UD-001`) — **required route, not yet implemented** | Brand listing: browse the active brands of the store | **Not found** — no brand route exists in `src/apps/storefront/urls.py`. A `Brand` model (`src/apps/catalog/models.py:67-79`) and `BrandViewSet` (`src/apps/catalog/api.py:187-201`, anonymous list/retrieve, slug lookup, `search`/`ordering`) exist, but no storefront page or Vue route exists | — | Absent — no storefront rendering path | Absent (no zone declared) | `No identified coverage` for a brand page (API viewset covered by `tests/test_api/test_catalog_api.py`) | **Required in V1** (approved 2026-10-22; `FR-CAT-006`). Not implemented: no route, no view, no template, no Vue route. `BrandViewSet.get_queryset()` currently returns all brands, so inactive brands are publicly listable and the public exposure rule is not yet met | FR-CAT-006, AC-CAT-006, FR-THEME-LAYOUT-001, AC-THEME-LAYOUT-012 |
| **Proposed route** `brands/<slug:slug>/` (path and URL name are placeholders; final route naming is an architecture decision, `UD-001`) — **required route, not yet implemented** | Brand detail: the brand's published products with browsing, filtering, and sorting | **Not found** — no brand detail route, view, or template exists. The API already supports `?brand=<slug>` product filtering (`src/apps/catalog/api.py:86`) and `/api/v1/brands/<slug>` | — | Absent — no storefront rendering path | Absent (no zone declared) | `No identified coverage` for a brand detail page | **Required in V1** (approved 2026-10-22; `FR-CAT-006`). Not implemented. Brand information must additionally support a logo and SEO metadata (`FR-CAT-007`); the `Brand` model currently has neither, and the existing `SEOMixin` pattern (`src/apps/cms/models.py`) is the available precedent | FR-CAT-006, FR-CAT-007, AC-CAT-006, AC-CAT-007, FR-THEME-LAYOUT-010, AC-THEME-LAYOUT-012 |
| `search/autocomplete/` (name `autocomplete`) | Type-ahead suggestions | Django view `autocomplete_view` (`views.py:208-219`) — JSON | Non-page (JSON) | Not applicable | Not applicable | `No identified coverage` for the JSON endpoint | Non-page response; must still be classified in the coverage record | FR-THEME-LAYOUT-010 |
| `search/suggest/` (name `suggest`) | Search suggestion list | Django view `suggest_view` (`views.py:221-232`) — JSON | Non-page (JSON) | Not applicable | Not applicable | `No identified coverage` for the JSON endpoint | Non-page response | FR-THEME-LAYOUT-010 |

### 4.3 Cart, wishlist, and compare

| Route / URL pattern | Page / user journey | Implementation | Template / component | Theme integration | Widget Zone integration | Tests | Status / gaps | Traceability |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `cart/` (name `cart`) | View cart lines and totals | `spa_page(cart_view, hook="cart_page")` (`urls.py:58`) → Vue `CartView.vue` when the SPA is enabled, else Django `cart_view` (`views.py:234-291`) | `storefront/cart.html` extends `storefront/base.html`; Vue `src/frontend/src/views/CartView.vue` | **Partial** — the Django path is theme-overridable; the Vue path has no component-level theme resolution (theme branding/CSS only, via the bootstrap payload) | Zone present in the Django path only: `cart_page` (cart.html:5) | `tests/test_storefront/test_storefront.py` (`test_cart_page_with_session`, `test_cart_page_rich_layout`); `tests/test_plugins/test_ajax_cart_plugin.py` | Dual rendering path: the same URL is served by two different implementations depending on the setting; the plugin can claim the route and force the Django path | FR-CART-001, FR-THEME-LAYOUT-001, FR-THEME-LAYOUT-010, AC-CART-001, AC-THEME-LAYOUT-012 |
| `wishlist/` (name `wishlist`) | Saved products | `spa_page(wishlist_view)` → Vue `WishlistView.vue` / Django `wishlist_view` (`views.py:433-436`) | `storefront/wishlist.html`; Vue `src/frontend/src/views/WishlistView.vue` | **Partial** (as above) | Absent in both paths | `tests/test_storefront/test_storefront.py` (`test_wishlist_add_works_for_authenticated_user`) | Login required (`@login_required`); Vue path uses `/api/v1/storefront/wishlist` | FR-THEME-LAYOUT-001, FR-THEME-LAYOUT-010, AC-THEME-LAYOUT-012 |
| `compare/` (name `compare`) | Product comparison | `spa_page(compare_view)` → Vue `CompareView.vue` / Django `compare_view` (`views.py:468-471`) | `storefront/compare.html`; Vue `src/frontend/src/views/CompareView.vue` | **Partial** | Absent | `tests/test_storefront/test_storefront.py` (`test_compare_flow_in_views`) | — | FR-THEME-LAYOUT-001, FR-THEME-LAYOUT-010, AC-THEME-LAYOUT-012 |
| `cart/add/<int:product_id>/`, `cart/update/<int:item_id>/`, `wishlist/add/<int:product_id>/`, `wishlist/move/<int:product_id>/`, `compare/add/<int:product_id>/`, `compare/remove/<int:product_id>/` | Form actions from the server-rendered pages | Django views `add_to_cart_view`, `update_cart_item_view`, `wishlist_add_view`, `wishlist_move_to_cart_view`, `compare_add_view`, `compare_remove_view` (`views.py:293-335, 439-492`) | Non-page (redirect / response) | Not applicable | Not applicable | `tests/test_storefront/test_storefront.py` (`test_add_to_cart_post_adds_item`, `test_wishlist_add_*`, `test_compare_flow_in_views`) | Action endpoints, not pages; not theme-relevant | FR-CART-001, FR-THEME-LAYOUT-010 |

### 4.4 Checkout and order confirmation

| Route / URL pattern | Page / user journey | Implementation | Template / component | Theme integration | Widget Zone integration | Tests | Status / gaps | Traceability |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `checkout/` (name `checkout`) | Checkout form (address, shipping, payment) | `spa_page(checkout_view)` → Vue `CheckoutView.vue` / Django `checkout_view` (`views.py:336-386`) | `storefront/checkout.html` extends `storefront/base.html`; Vue `src/frontend/src/views/CheckoutView.vue` | **Partial** | Absent in both paths | `tests/test_storefront/test_storefront.py` (`test_checkout_page_and_flow`); `tests/test_api/test_cart_checkout_api.py` | The Django path renders `storefront/order_detail.html` as the order confirmation after a successful POST (`views.py:367`) — there is no separate confirmation template | FR-CHK-001, FR-THEME-LAYOUT-001, AC-CHK-001, AC-THEME-LAYOUT-012 |
| `orders/<str:number>/` (name `order_detail`) | Order confirmation / order detail | `spa_page(order_detail_view)` → Vue `OrderView.vue` / Django `order_detail_view` (`views.py:494-499`) | `storefront/order_detail.html` extends `storefront/base.html`; Vue `src/frontend/src/views/OrderView.vue` | **Partial** | Absent | `tests/test_storefront/test_storefront.py` (checkout flow reaches the order page); `tests/test_api/test_orders_payments_shipping_api.py` | Same template serves both "order confirmation" and "order detail"; the two page types are not distinguished in the implementation | FR-ORD-001, FR-THEME-LAYOUT-001, AC-ORD-001, AC-THEME-LAYOUT-012 |

### 4.5 Customer: registration, login, profile, account

| Route / URL pattern | Page / user journey | Implementation | Template / component | Theme integration | Widget Zone integration | Tests | Status / gaps | Traceability |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `register/` (name `register`) | Customer registration | `spa_page(register_view)` → Vue `RegisterView.vue` / Django `register_view` (`views.py:389-402`) | `storefront/register.html`; Vue `src/frontend/src/views/RegisterView.vue` | **Partial** | Absent | `tests/test_storefront/test_storefront.py` (`test_register_login_account_flow`); `tests/test_api/test_auth_api.py` | — | FR-CUST-001, FR-THEME-LAYOUT-001, AC-CUST-001, AC-THEME-LAYOUT-012 |
| `login/` (name `login`) | Customer login | `spa_page(login_view)` → Vue `LoginView.vue` / Django `login_view` (`views.py:405-419`) | `storefront/login.html`; Vue `src/frontend/src/views/LoginView.vue` | **Partial** | Absent | `tests/test_storefront/test_storefront.py` (`test_register_login_account_flow`); `tests/test_api/test_auth_api.py` | — | FR-CUST-001, FR-THEME-LAYOUT-001, AC-CUST-001, AC-THEME-LAYOUT-012 |
| `logout/` (name `logout`) | Sign out | Django view `logout_view` (`views.py:422-424`) | Non-page (redirect) | Not applicable | Not applicable | `tests/test_storefront/test_storefront.py` (used inside the register/login flow) | Action endpoint | FR-CUST-001, FR-THEME-LAYOUT-010 |
| `account/` (name `account`) | Customer account: profile summary and recent orders | `spa_page(account_view)` → Vue `AccountView.vue` / Django `account_view` (`views.py:427-430`, `@login_required`) | `storefront/account.html`; Vue `src/frontend/src/views/AccountView.vue` | **Partial** | Absent | `tests/test_storefront/test_storefront.py` (`test_register_login_account_flow`, `test_account_requires_login`, `test_account_empty_orders_keeps_its_own_wording`) | The account page shows the order history only; the address book is a separate required route (see the next row) | FR-CUST-001, FR-THEME-LAYOUT-001, AC-CUST-001, AC-THEME-LAYOUT-012 |
| **Proposed route** `account/addresses/` (path and URL name are placeholders; final route naming is an architecture decision, `UD-001`) — **required route, not yet implemented** | Customer address book: list, create, update, and delete the customer's own saved addresses and designate a default | **Not found** — no address route, view, template, or Vue route exists, and no customer-owned address entity exists in the code. Only the order-scoped `OrderAddress` snapshot (`src/apps/orders/models.py:116-138`) and raw checkout form fields (`views.py:348-357`) exist | — | Absent — no storefront rendering path | Absent (no zone declared) | `No identified coverage` | **Required in V1** (approved 2026-10-22; `FR-CUST-002`). Not implemented: data entity, API, and page are all missing. Staff view-only administrative access and checkout selection of an owned address are required (`FR-CHK-001`, `AC-CHK-002`) | FR-CUST-002, FR-CHK-001, AC-CUST-002, AC-CHK-002, FR-THEME-LAYOUT-001, AC-THEME-LAYOUT-012 |

### 4.6 Content pages, blog, and informational pages

| Route / URL pattern | Page / user journey | Implementation | Template / component | Theme integration | Widget Zone integration | Tests | Status / gaps | Traceability |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `<slug:slug>/` (name `cms_page`, catch-all, last pattern) | CMS informational page | Django view `cms_page_view` (`views.py:502-505`) | `storefront/cms_page.html` extends `storefront/base.html` | Existing — Django template override | Absent | `tests/test_cms/test_cms_media_seo.py` (CMS model level); `No identified coverage` for the storefront page rendering | Catch-all pattern — any unmatched single-segment path is resolved as a CMS page. It is **not** the Contact Us page: a dedicated contact route is required (see the next row) | FR-THEME-LAYOUT-001, FR-THEME-LAYOUT-010, AC-THEME-LAYOUT-012 |
| **Proposed route** `contact/` (path and URL name are placeholders; final route naming is an architecture decision, `UD-001`) — **required route, not yet implemented** | Contact Us: store contact information and a validated inquiry form | **Not found** — no contact route, view, template, inquiry model, or Vue route exists. The CMS catch-all pattern is explicitly not accepted as a substitute (approved 2026-10-22) | — | Absent — no storefront rendering path | Absent (no zone declared) | `No identified coverage` | **Required in V1** (approved 2026-10-22; `FR-CONTACT-001`). Not implemented: a valid inquiry must be stored and a notification sent through the existing notification capabilities (`apps/notifications`, `core/notifications`). CAPTCHA applicability for the form remains open (`UD-021`) | FR-CONTACT-001, AC-CONTACT-001, FR-THEME-LAYOUT-001, AC-THEME-LAYOUT-012 |
| `blog/` (name `blog`) | Blog listing | Django view `blog_list_view` (`views.py:508-510`) | `storefront/blog_list.html` extends `storefront/base.html` | Existing — Django template override | Absent | `tests/test_storefront/test_storefront_api.py` (`test_page_and_blog_endpoints` — API level) | No Vue route exists for the blog | FR-THEME-LAYOUT-001, FR-THEME-LAYOUT-010, AC-THEME-LAYOUT-012 |
| `blog/<slug:slug>/` (name `blog_detail`) | Blog post | Django view `blog_detail_view` (`views.py:513-516`) | `storefront/blog_detail.html` extends `storefront/base.html` | Existing — Django template override | Absent | `tests/test_storefront/test_storefront_api.py` (API level) | No Vue route exists for blog posts | FR-THEME-LAYOUT-001, FR-THEME-LAYOUT-010, AC-THEME-LAYOUT-012 |

### 4.7 Shared layout, header, navigation, footer, and error pages

| Route / URL pattern | Page / user journey | Implementation | Template / component | Theme integration | Widget Zone integration | Tests | Status / gaps | Traceability |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| *(layout, not a route)* | Site shell: head, header, navigation, search, account actions, language/currency switchers, messages, footer | Django template `storefront/base.html` (98 lines) — the single layout used by **all** 15 Django-rendered storefront pages | `storefront/base.html`; Vue equivalents `src/frontend/src/components/SiteHeader.vue`, `SiteFooter.vue`, `src/frontend/src/App.vue` | **Partial** — a theme can replace `base.html` wholesale (Django path only) or override two fragment includes; the Vue shell has a fixed structure with no theme-provided root layout | Zones in the Django layout: `head` (base.html:10), `header_cart` (base.html:29), `body_end` (base.html:96) | `tests/test_storefront/test_storefront.py` (`test_theme_branding_in_base`, `test_admin_link_shown_only_for_staff`); `tests/test_storefront/test_theme_pacific.py` | Two distinct shells exist (Django `base.html`, Vue `App.vue`) with duplicated header/footer logic; the navigation menu comes from the CMS `Menu` model in both paths | FR-THEME-LAYOUT-002/003, FR-THEME-LAYOUT-010, FR-EXT-004, AC-THEME-LAYOUT-012 |
| *(theme fragment override, not a route)* | Theme banner and footer note | Theme-provided fragments included by `base.html:15, 92` | `storefront/theme_banner.html`, `storefront/theme_footer.html` (app defaults); `src/themes/default/templates/storefront/theme_banner.html`, `theme_footer.html`; `src/themes/alt-theme/templates/storefront/theme_banner.html`; `src/plugins/theme_pacific/templates/storefront/theme_banner.html`, `theme_footer.html` | Existing — the only guaranteed theme override surface in the core layout | Absent | `tests/test_storefront/test_storefront.py` (`test_theme_template_override_mechanism`); `tests/test_storefront/test_theme_pacific.py` (`test_pacific_theme_renders_when_active`) | `alt-theme` ships a banner but no footer fragment; the app default is used for the missing one | FR-THEME-LAYOUT-006, FR-THEME-LAYOUT-011, AC-THEME-LAYOUT-014 |
| *(error pages, not routes)* | 404 / 500 error pages | **Not found** — no `404.html` / `500.html` template and no `handler404` in the project; Django's default error pages are used | — | Absent | Not applicable | `No identified coverage` | Error pages are outside theme coverage today; `FR-THEME-LAYOUT-001` requires that any route outside theme coverage be explicitly documented | FR-THEME-LAYOUT-001, FR-THEME-LAYOUT-010, AC-THEME-LAYOUT-012 |
| `robots.txt` (name `robots`) | Crawler directives | Django view `robots_txt_view` (`views.py:559-563`) — text | Non-page | Not applicable | Not applicable | `No identified coverage` | Non-page response | FR-THEME-LAYOUT-010 |
| `sitemap.xml` (name `sitemap`) | Sitemap | Django view `sitemap_xml_view` (`views.py:566-578`) — XML | Non-page | Not applicable | Not applicable | `No identified coverage` | Non-page response | FR-THEME-LAYOUT-010 |
| `i18n/setlang/`, `i18n/setcurrency/` (names `set_language`, `set_currency`) | Language / currency selection | Django views `set_language_view` (`views.py:519-537`), `set_currency_view` (`views.py:539-557`) — redirect + cookie | Non-page | Not applicable | Not applicable | `tests/test_stores/test_translations.py` (`test_set_language_view_sets_cookie`); `tests/test_storefront/test_storefront_api.py` (`test_set_currency_view_sets_cookie`) | Language and currency are selected by cookie, not by a themed control | FR-I18N-001, FR-CUR-001, FR-THEME-LAYOUT-010 |

### 4.8 Non-storefront surfaces (classified for completeness)

| Route / URL pattern | Page / user journey | Implementation | Template / component | Theme integration | Widget Zone integration | Tests | Status / gaps | Traceability |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `admin/` | Administration interface | Custom `AdminSite` (`src/apps/admin_panel/admin_site.py`) | `src/templates/admin/base_site.html`, `nav_sidebar.html`; `admin_panel` templates | Separate layout — storefront theme activation does not affect the admin (enforced by separate template/static paths) | Admin has no storefront hook zones; admin zones are not defined | `tests/test_admin/` (multiple files) | Must remain outside storefront theme coverage | FR-ADMIN-003, FR-THEME-LAYOUT-010, AC-ADMIN-003, AC-THEME-LAYOUT-013 |
| `health/` | Health probe | `core.health.views.health_check` | — | Not applicable | Not applicable | `tests/test_health.py` | Non-storefront | FR-THEME-LAYOUT-010 |
| `plugins/` | Plugin asset/URL surface | `core.plugins.urls` | — | Not applicable | Not applicable | `tests/test_plugins/` | Not a storefront page | FR-PLUG-001, FR-THEME-LAYOUT-010 |
| `api/<version>/…` | Programmatic API (auth, customers, cart, checkout, payments, shipping, catalog, orders, reviews, webhooks, storefront bootstrap/hooks/search/pages/blog/wishlist/compare) | DRF viewsets and APIViews (`src/config/api_urls.py`) | — | Not applicable | `storefront/hooks/<hook_name>` returns plugin fragments as JSON (`api.py:176-182`) | `tests/test_api/` (7 files), `tests/test_storefront/test_storefront_api.py` | The hook API exists, but no Vue component calls it (see §6) | FR-THEME-LAYOUT-010, NFR-API-001 |

### 4.9 Vue route inventory (current SPA)

The SPA router (`src/frontend/src/router/index.js`) registers exactly nine
routes: `cart`, `checkout`, `login`, `register`, `account`, `wishlist`,
`compare`, `order` (`/orders/:number/`), and a `not-found` catch-all. The
router file itself states that content pages "are server-rendered by Django
and are reached via normal full-page links. The SPA only owns the interactive
routes below."

| Vue route | Component | Paired Django route / template | Theme integration | Widget Zone integration |
| --- | --- | --- | --- | --- |
| `/cart/` | `src/frontend/src/views/CartView.vue` | `cart/` → `storefront/cart.html` | Partial (branding/CSS via bootstrap payload) | Absent |
| `/checkout/` | `CheckoutView.vue` | `checkout/` → `storefront/checkout.html` | Partial | Absent |
| `/login/` | `LoginView.vue` | `login/` → `storefront/login.html` | Partial | Absent |
| `/register/` | `RegisterView.vue` | `register/` → `storefront/register.html` | Partial | Absent |
| `/account/` | `AccountView.vue` | `account/` → `storefront/account.html` | Partial | Absent |
| `/wishlist/` | `WishlistView.vue` | `wishlist/` → `storefront/wishlist.html` | Partial | Absent |
| `/compare/` | `CompareView.vue` | `compare/` → `storefront/compare.html` | Partial | Absent |
| `/orders/:number/` | `OrderView.vue` | `orders/<str:number>/` → `storefront/order_detail.html` | Partial | Absent |
| `/:pathMatch(.*)*` | `NotFoundView.vue` | No Django counterpart | Absent (SPA-only not-found view) | Absent |

No Vue route exists for home, category, product, search, blog, or CMS pages.
The routes required in V1 but not yet implemented — brand listing, brand
detail, the customer address book, and the dedicated Contact Us page (§4.2,
§4.5, §4.6) — are likewise absent from the Vue router; each becomes a Vue
route when it is migrated.

## 5. Theme Coverage as Implemented

1. **Activation.** The active theme is the `ACTIVE_THEME` environment value
   read in `src/config/settings/base.py:80` and exposed through
   `get_active_theme_name()` (`src/apps/storefront/themes.py:9-10`). There is
   **no persisted activation, no administrative activation action, and no
   runtime invalidation** in the current implementation. This is the recorded
   implementation gap `CF-003` in `REQUIREMENTS.md` §6.1 and remains open as
   `UD-002`.
2. **Override surface for a theme.** A theme directory contributes
   `templates/` and `static/` only. Within the core layout the guaranteed
   override points are two fragment includes — `storefront/theme_banner.html`
   and `storefront/theme_footer.html` (`base.html:15, 92`). A theme may also
   replace whole page templates (as `theme_pacific` does for `base.html`,
   `home.html`, and `product_detail.html`), but that is full-template
   replacement, not component-level resolution.
3. **Theme assets.** The theme `static/` directory is added to
   `STATICFILES_DIRS`, and the SPA receives the theme's CSS file list through
   the bootstrap payload (`api.py:55-59, 103`) and injects it at runtime
   (`App.vue:29-36`). The Django layout links only `storefront/css/main.css`
   (`base.html:11`); the default theme's `src/themes/default/static/css/theme.css`
   is **not referenced by any template**, and the `pacific` theme only gets its
   CSS applied because its own `base.html` override links it explicitly.
4. **Consistency.** Because the SPA and the Django pages are separate shells
   (`App.vue` vs `base.html`), a theme can currently change the two paths
   differently: the Django path is template-overridable, the Vue path is
   limited to branding, CSS variables, and the theme stylesheet list.
5. **Theme configuration.** `theme.json` supplies `config`
   (`src/themes/default/theme.json`, `src/themes/alt-theme/theme.json`), and
   for plugin-provided themes the stored plugin settings are merged on top
   (`themes.py:49-69`). The config is exposed to the SPA through the
   bootstrap payload; the Django templates read branding from the
   `storefront` context processor.
6. **Coverage of the approved route list.** `FR-THEME-LAYOUT-001` names
   home, product listing/category/brand, product details, search, cart,
   checkout and order confirmation, registration/login/account, wishlist,
   compare, order history/details, contact and informational/CMS pages, and
   blog/news. As approved on 2026-10-22, **brand listing and brand detail
   pages, the customer address book, and a dedicated Contact Us page are
   required in V1** and are recorded as required-but-not-implemented routes
   in §4.2, §4.5, and §4.6. The Vue path still covers none of the content
   pages.

## 6. Widget Zone (Plugin Hook) Coverage as Implemented

| Hook zone | Location (server-rendered) | Plugins contributing (evidence) | Vue equivalent |
| --- | --- | --- | --- |
| `head` | `storefront/base.html:10`; `theme_pacific/.../base.html:10` | `ajax_cart` → `ajax_cart/head.html` (`src/plugins/ajax_cart/plugin.py:6-12`) | **None** |
| `header_cart` | `storefront/base.html:29` (falls back to the default cart link when no plugin contributes) | `ajax_cart` → `ajax_cart/cart_button.html` | **None** |
| `body_end` | `storefront/base.html:96`; `theme_pacific/.../base.html:95` | `ajax_cart` → `ajax_cart/drawer.html` | **None** |
| `home_top` | `storefront/home.html:5`; `theme_pacific/.../home.html:5` | No plugin registers this zone | **None** |
| `home_middle` | `storefront/home.html:10`; `theme_pacific/.../home.html:25` | `slider` → `slider/slider.html`; `flash_sale` → `flash_sale/section.html` | **None** |
| `home_bottom` | `storefront/home.html:28`; `theme_pacific/.../home.html:39` | No plugin registers this zone | **None** |
| `cart_page` | `storefront/cart.html:5`; also used as a **route claim** (`urls.py:58`, `_plugin_claims`) | `ajax_cart` → `ajax_cart/cart_page.html` | **None** |

Findings:

1. **The zones are plugin-hook names, not a Widget Zone registry.** They are
   arbitrary strings registered per plugin through
   `Plugin.get_storefront_hooks()`; there is no central registry, no zone
   identifier contract, no declared capabilities, and no ordering contract
   beyond plugin discovery order (`hooks.py:18-20`).
2. **Contribution is server-rendered HTML**, not a Vue component. The
   fragment is produced by `render_plugin_hook()` and either included in a
   Django template or exposed as JSON by `/api/v1/storefront/hooks/<name>`.
3. **The SPA does not consume plugin hooks at all.** No Vue file references a
   hook name, `v-html`, or the hooks endpoint; the only related code is an
   unused `widgets` getter in `src/frontend/src/stores/storefront.js:17`.
   The docstring in `src/apps/storefront/hooks.py:5-7` states that both the
   template tag and the Vue SPA consume the same fragments — this is **not
   true in the current code** and is recorded as a documentation/code
   discrepancy.
4. **CMS widgets are data-only.** `apps.cms.models.Widget` records are exposed
   through the bootstrap payload (`api.py:68-71`) but are not rendered by any
   Django storefront template and are not consumed by any Vue component.
   `ContentBlock` records are likewise not rendered by the storefront.
5. **No zone exists on** category, product detail, search, blog, CMS, account,
   checkout, wishlist, compare, or order detail pages.
6. **Actual Vue rendering is now a binding requirement.** As approved on
   2026-10-22, a zone declared for a route in this record must be rendered by
   the Vue storefront on that route, an enabled plugin's contribution must
   appear in the rendered output, and a route without a contribution must
   render the zone's documented empty or fallback state
   (`FR-EXT-001`, `AC-THEME-LAYOUT-009`, `AC-ZONE-003`), verified with Vitest
   (`NFR-TEST-001`). The zone identifiers, capabilities, and ordering remain
   open design decisions (`UD-006`, `UD-007`); the rendering obligation does
   not. The routes required in V1 but not yet implemented (§4.2 brand
   listing/brand detail, §4.5 address book, §4.6 Contact Us) will require
   their own zone coverage once the zone registry is defined, and their
   "Absent" zone state in this record reflects the current implementation,
   not a reduced requirement.

## 7. Gaps and Unverified Items

**Gaps (evidence-based)**

| # | Gap | Evidence |
| --- | --- | --- |
| G-1 | No Vue route for any content page; six of the nine SPA routes shadow Django templates for the same URL | `src/frontend/src/router/index.js:3-16`; `src/apps/storefront/urls.py:47-65` |
| G-2 | Two independent shells (Django `base.html`, Vue `App.vue`) with duplicated header/footer/navigation logic | `base.html:16-69` vs `App.vue:42-49`, `SiteHeader.vue:44-106` |
| G-3 | Plugin hook zones exist only in the Django path; the SPA renders no plugin content | §6 finding 3 |
| G-4 | Theme activation is environment-driven, not persisted or administratively actionable | `base.py:80`; `themes.py:9-10`; `CF-003` in `REQUIREMENTS.md` §6.1 |
| G-5 | Theme CSS is not linked by the core Django layout | `base.html:11`; `src/themes/default/static/css/theme.css` unreferenced |
| G-6 | Brand listing/detail, the customer address book, and a dedicated Contact Us page are required in V1 (approved 2026-10-22) but have no implementation; the brand routes also need brand logo/SEO data and public filtering of inactive brands | §4.2, §4.5, §4.6 |
| G-7 | No filtering/sorting/paging on the category page (API supports it) | `views.py:81-90`; `catalog/api.py:92-94` |
| G-8 | No 404/500 templates; error pages are outside theme coverage | §4.7 |
| G-9 | The SPA build output is git-ignored and not reproducible from a clone | `.gitignore`; `vite.config.js` |
| G-10 | The SPA hardcodes English UI strings; the DB word collection is not used in the Vue layer | `SiteHeader.vue:55-71`; `App.vue:21-23` |
| G-11 | The hook API docstring claims SPA consumption that does not exist | `hooks.py:5-7` vs `src/frontend/src/**` |

**Not verified (could not be established from the repository)**

- Whether any plugin other than the four in-tree plugins contributes to a
  storefront zone: only `src/plugins/*` was inspected; third-party plugins
  are not in the repository.
- Whether the `flash_sale` admin pages are rendered by any storefront
  template: they are admin views, and the plugin registers only the
  `home_middle` storefront hook. The `sample_plugin` fragment
  (`sample_plugin/hello.html`) is **not reachable** from any storefront
  template: `sample_plugin` defines no `get_storefront_hooks()` and no
  template calls a zone it registers.
- Whether the `alt-theme` footer fragment is intentionally absent or missing
  (no manifest field declares required fragments).
- Runtime behavior of the SPA build in a production-like deployment (no
  deployment manifests exist in the repository — `ARCHITECTURE.md` §2.1, G11).

## 8. Test Coverage Observations

- **Storefront page rendering:** `tests/test_storefront/test_storefront.py`
  (28 tests) covers home, category, product detail, cart, checkout, register,
  login, account, wishlist, and compare in the Django rendering path.
- **Theme behavior:** `tests/test_storefront/test_theme_pacific.py` (8 tests)
  covers plugin-theme discovery, configuration merging, plugin lifecycle, and
  rendering with the `pacific` theme active; `test_theme_template_override_mechanism`
  in `test_storefront.py` covers the fragment override.
- **Storefront API:** `tests/test_storefront/test_storefront_api.py` (19
  tests) covers bootstrap, currencies, the hooks endpoint, search, pages, and
  blog.
- **Plugin behavior:** `tests/test_plugins/` covers the `ajax_cart`, `slider`,
  and `flash_sale` plugins, but **no test asserts that a plugin fragment is
  rendered inside a storefront page**; the hook coverage is limited to the
  JSON endpoint.
- **Missing coverage that would help verify theme coverage:**
  1. A test asserting that every page in the coverage record is reachable and
     renders under the active theme (today only `home` and `product_detail`
     are proven to be theme-overridable).
  2. A test asserting that a theme switch changes the rendered output of each
     route class.
  3. A test asserting that every zone declared in the coverage record is
     either rendered or explicitly marked as not applicable.
  4. A test for the SPA rendering path. **Vitest is the approved framework
     for Vue component and Widget Zone tests** (approved decision 2026-10-22;
     `NFR-TEST-001`, `AC-ZONE-003`), but the frontend project currently has
     no test script and no test runner — `src/frontend/package.json` has no
     `test` script — so the harness itself is part of the outstanding work.

## 9. Traceability

| Identifier | Source | How this record applies |
| --- | --- | --- |
| `UD-001` — Vue route coverage and migration (before architecture) | `REQUIREMENTS.md` §6.2 | §4 classifies every concrete storefront route as Vue-served, Django-served, or API-only/non-page, and §5–§6 map the theme and hook integration per route. Final route/component names remain an architecture decision, as the identifier states |
| `FR-THEME-LAYOUT-010` — Global Storefront Coverage and Traceability | `REQUIREMENTS.md` §1.13 | §4 provides the page-type → route → implementation → template/component mapping; §5 records which routes are outside theme coverage (brand pages, address management, contact page, error pages) |
| `AC-THEME-LAYOUT-012` — coverage record completeness | `REQUIREMENTS.md` §4.1 | §4 covers all 28 route patterns in `src/apps/storefront/urls.py`, the two non-page storefront surfaces, the SPA route inventory (§4.9), and the non-storefront surfaces (§4.8). The record is **not** yet a compliance statement for `AC-THEME-LAYOUT-012`: that criterion additionally requires root-layout, shared-component, layout-variant, and Widget Zone identifiers per route, which do not exist in the implementation (gaps G-2, G-3) |
| `FR-THEME-LAYOUT-001` — Global Theme Activation (route list) | `REQUIREMENTS.md` §1.13 | §5.6 compares the approved route list against the implementation (gaps G-6) |
| `FR-THEME-LAYOUT-002/003/005/006/011` | `REQUIREMENTS.md` §1.13 | §5 describes the current root layout, shared components, override surface, package structure, and asset delivery as evidence for the later design work |
| `FR-EXT-001` – `FR-EXT-004`, `FR-THEME-001/002` | `REQUIREMENTS.md` §1.12 | §6 records the existing hook mechanism as the only plugin UI contribution path |
| `FR-CAT-005`, `FR-CART-001`, `FR-CHK-001`, `FR-ORD-001`, `FR-CUST-001`, `FR-CAT-002/003/004` | `REQUIREMENTS.md` §1.3–§1.5 | §4 cites the requirement each page group implements, and records where the implementation is narrower than the requirement (G-6, G-7) |
| `FR-ADMIN-003`, `AC-THEME-LAYOUT-013` | `REQUIREMENTS.md` §1.1, §4.1 | §4.8 records that the admin has a separate layout and no storefront zones |
| `ARCHITECTURE.md` §5 G1, §6.2 S0/S1, §7, D3, D4 | `ARCHITECTURE.md` | §3–§6 provide the repository evidence for the storefront route-ownership gap (G1) and the theme/widget-zone direction (S1/S2) |
| `CF-002`, `CF-003`, `CF-004` | `REQUIREMENTS.md` §6.1 | Confirmed in this record: the Django/Vue hybrid persists (CF-002), activation is environment-driven (CF-003), and no Widget Zone registry exists (CF-004) |

**Issue recorded, not corrected:** `FR-THEME-LAYOUT-001` names brand pages and
`REQUIREMENTS.md` §5.2 lists a "Brand" page type, while the implementation
has no brand page. This record classifies the route as **Not found** and does
not change the requirement; resolving it (implement a brand page, or
explicitly scope it out) is a scope decision for the user.

## 10. Validation Performed

- Every route pattern in §4 was read from `src/apps/storefront/urls.py` and
  traced to its view in `src/apps/storefront/views.py`; every template path
  cited was verified to exist under
  `src/apps/storefront/templates/storefront/`. The rows marked as required
  but not yet implemented (§4.2 brand listing and brand detail, §4.5 address
  book, §4.6 Contact Us) are **proposed** route paths and names, not existing
  routes; the final route naming remains an architecture decision (`UD-001`).
- Every hook name and location was verified by searching `{% plugin_hook %}`
  usage across all templates and `get_storefront_hooks()` across all plugins.
- Every file path in this document was listed from the working tree before
  being cited.
- The absence of brand routes, address-management routes, contact pages, and
  404/500 templates was verified by searching the URL configuration, the
  storefront views, the template directories, and the project template
  directory.
- The Vue route inventory was read from `src/frontend/src/router/index.js`;
  the absence of hook/widget rendering in the SPA was verified by searching
  all `.vue` and `.js` files under `src/frontend/src`.
- **No test suite was executed for this document**, because it changes no
  application code; the test references above are file and test-name
  citations taken from the repository, not execution results. No migration
  was run and no database was modified.

## 11. Resolved Decisions and Remaining Questions

**Resolved by approved decision (2026-10-22):**

1. **Brand page** — brand listing and brand detail pages are required in V1
   (`FR-CAT-006` – `FR-CAT-007`); they are recorded as required routes in
   §4.2, not as routes outside theme coverage.
2. **Customer address management** — a customer-managed address book is
   required in V1 (`FR-CUST-002`, `FR-CHK-001`); it is recorded as a
   required route in §4.5.
3. **Contact page** — a dedicated Contact Us route and page are required in
   V1; the CMS catch-all route is explicitly not accepted as a substitute
   (`FR-CONTACT-001`). Recorded in §4.6.
4. **Renderer and sequencing** — the Vue storefront is the target renderer
   for the supported routes, and the approved sequence is that preliminary
   Theme and Widget Zone work may precede the content-page migration while
   **completion** of the full Theme and Widget Zone system follows it
   (`PROJECT_SCOPE.md` §6.5, `REQUIREMENTS.md` §6.1 CF-010). Route-by-route
   migration state and actual Widget Zone rendering state are tracked in
   this record.
5. **Vue test framework** — Vitest is the approved framework for Vue
   component and Widget Zone tests (`NFR-TEST-001`, `AC-ZONE-003`); the
   frontend project currently has no test runner (§8).

**Remaining questions:**

1. Should the **hook API docstring** (`src/apps/storefront/hooks.py:5-7`) be
   corrected to match the verified behavior, or should SPA hook consumption be
   scheduled as work?

---

**End of document.**
