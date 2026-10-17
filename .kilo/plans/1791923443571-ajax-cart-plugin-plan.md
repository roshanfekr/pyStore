# Plan: AjaxCart plugin (Bootstrap drawer + modern cart page)

## Goal
Add a storefront plugin named **AjaxCart** (`id: ajax_cart`) that, when enabled, provides:
1. A modern **Bootstrap offcanvas cart drawer** with AJAX add/update/remove, available on server-rendered storefront pages.
2. A modern **Bootstrap cart page** that takes over `/cart/` (even when the Vue SPA is enabled).

The default/SPA cart is left as-is (only the plugin is in scope).

## Confirmed decisions (from user)
- Deliverable: drawer **and** modern cart page.
- `/cart/` is taken over by the plugin when enabled (SPA bypassed for that route).
- The current/default cart is not restyled; the plugin is the fix.

## Key codebase facts (verified)
- Plugins: `src/plugins/<id>/` with `plugin.json` + `plugin.py`; auto-added to `INSTALLED_APPS` via `core/plugins/loader.get_discovered_plugin_apps()`, so their `templates/` and `static/` are served.
- Storefront injection point: `{% plugin_hook 'name' %}` (`apps/storefront/templatetags/plugin_hooks.py` → `apps/storefront/hooks.render_plugin_hook`). Hook partials get `request`, `plugin_id`, `plugin_settings`, and `get_hook_context()`.
- Storefront `base.html` (default + pacific) currently has **no** plugin hook points.
- Cart page: `/cart/` → `spa_page(views.cart_view)` in `apps/storefront/urls.py`; serves the SPA shell when `STOREFRONT_SPA_ENABLED` (default True in dev), else `storefront/cart.html`.
- Cart JSON API already exists (`config/api_urls.py`): `GET /api/v1/cart`, `POST /api/v1/cart/items`, `PATCH|DELETE /api/v1/cart/items/<item_id>`, `POST|DELETE /api/v1/cart/coupon`. Guest cart uses the Django session (same cart as the SSR pages).
- Bootstrap 5 is already vendored: `src/apps/admin_panel/static/admin_panel/vendor/bootstrap/bootstrap.min.css` and `bootstrap.bundle.min.js` (referenced in `src/templates/admin/base_site.html`). Reuse it; no download.
- CSP: `script-src 'self'` (no inline JS/CDN), `style-src 'self' 'unsafe-inline'` → all JS must be external plugin files.
- Add-to-cart form (identical in `storefront/product_detail.html` and `theme_pacific/.../product_detail.html`): `form.product-buy` posting to `storefront:add_to_cart` with `product.id`, `variant` (variant **id**), `quantity`.
- `BaseModel` uses integer PKs (so `<int:...>` URLs and integer `item_id` are correct).

## Core changes (small, required)

1. `src/apps/storefront/templates/storefront/base.html`
   - Add `{% load plugin_hooks %}` near the top.
   - Insert `{% plugin_hook 'head' %}` **immediately before** the `storefront/css/main.css` `<link>` (so theme CSS loads after Bootstrap and wins on shared classes).
   - Replace the header Cart link with:
     ```django
     {% plugin_hook 'header_cart' as plugin_header_cart %}
     {% if plugin_header_cart %}{{ plugin_header_cart }}{% else %}<a href="{% url 'storefront:cart' %}">{% tr 'Cart' %}</a>{% endif %}
     ```
   - Add `{% plugin_hook 'body_end' %}` just before `</body>`.

2. `src/plugins/theme_pacific/templates/storefront/base.html`
   - Same three changes (`head` before `main.css`, `header_cart`, `body_end`).

3. `src/apps/storefront/templates/storefront/cart.html`
   - Add `{% load plugin_hooks %}` and wrap the existing cart body:
     ```django
     {% plugin_hook 'cart_page' as plugin_cart_page %}
     {% if plugin_cart_page %}{{ plugin_cart_page }}{% else %} …existing markup… {% endif %}
     ```
   - (Shared app template, so this covers both themes; pacific does not override `cart.html`.)

4. `src/apps/storefront/urls.py` — let an enabled plugin claim a page:
   - `def spa_page(view, hook=None)`; in `dispatch`, serve the SPA only when `STOREFRONT_SPA_ENABLED` **and** no enabled plugin registers `hook`.
   - Add helper `_plugin_claims(hook)`: returns `False` if `hook is None`; else `PluginManager().enabled_storefront_hooks(hook)` wrapped in `try/except` → `bool(...)`.
   - Cart route: `path("cart/", spa_page(views.cart_view, hook="cart_page"), name="cart")`.

5. Product buy forms (both templates) — add AJAX data attributes:
   - `storefront/product_detail.html` and `theme_pacific/.../product_detail.html`:
     - `<form ... class="product-action product-buy" data-product-slug="{{ product.slug }}">`
     - variant `<option value="{{ v.id }}" data-sku="{{ v.sku }}">`

## Plugin files (new)

```
src/plugins/ajax_cart/
  __init__.py
  plugin.json                      # id "ajax_cart", name "AjaxCart", entry_point "plugin:AjaxCartPlugin"
  plugin.py                        # AjaxCartPlugin(Plugin)
  apps.py                          # AppConfig(name="plugins.ajax_cart", label="ajax_cart", verbose_name="AjaxCart")
  settings.py                      # DEFAULTS + SCHEMA
  templatetags/__init__.py
  templatetags/ajax_cart_tags.py   # {% ajax_cart_currency as c %} (symbol/decimals), optional helpers
  templates/ajax_cart/
    head.html                      # Bootstrap CSS <link> + ajax_cart.css <link>
    cart_button.html               # header cart button + badge (Bootstrap offcanvas trigger)
    drawer.html                    # offcanvas skeleton + Bootstrap JS + ajax_cart.js (defer)
    cart_page.html                 # modern cart page skeleton (same client-render target)
  static/ajax_cart/
    css/ajax_cart.css              # namespaced `.ajax-cart*` styles; theme colors via CSS vars
    js/ajax_cart.js                # fetch-based cart client
```

`plugin.py`:
```python
class AjaxCartPlugin(Plugin):
    def get_storefront_hooks(self):
        return {
            "head": ["ajax_cart/head.html"],
            "header_cart": ["ajax_cart/cart_button.html"],
            "body_end": ["ajax_cart/drawer.html"],
            "cart_page": ["ajax_cart/cart_page.html"],
        }
    def get_settings_defaults(self): return dict(DEFAULTS)
    def get_settings_schema(self): return dict(SCHEMA)
```

`plugin.json`: `{"id":"ajax_cart","name":"AjaxCart","version":"1.0.0","author":"pyStore","description":"Modern Bootstrap AJAX cart: offcanvas drawer and cart page.","dependencies":[],"minimum_core_version":"1.0.0","entry_point":"plugin:AjaxCartPlugin"}`

## AJAX contract (reuse the existing DRF cart API — no new endpoints)
- Add: `POST /api/v1/cart/items` `{product: <slug>, variant: <sku|omit>, quantity}` → returns full cart JSON (201).
- Update: `PATCH /api/v1/cart/items/<item_id>` `{quantity}` → full cart JSON.
- Remove: `DELETE /api/v1/cart/items/<item_id>` → 204 (then `GET /api/v1/cart`).
- Coupon: `POST /api/v1/cart/coupon` `{code}`; remove via `DELETE /api/v1/cart/coupon`.
- Initial/refresh: `GET /api/v1/cart` → `{lines:[{item_id,product_name,quantity,unit_price,line_total}], subtotal, discount_amount, total, coupon_code}`.
- Requests: `credentials: 'same-origin'`, `X-CSRFToken` from the `csrftoken` cookie (the drawer includes a hidden `{% csrf_token %}` so the cookie is always set). Guest cart resolves via the same session as SSR pages.
- Money: API returns raw decimals (e.g. `100.0000`); `ajax_cart.js` formats with symbol/decimals exposed by `{% ajax_cart_currency %}` as `data-` attributes on the drawer/page.

### Drawer/cart-page behavior (`ajax_cart.js`)
- On load: `GET /api/v1/cart` → render lines into the drawer and cart page, update header badge.
- Intercept submit on `form.product-buy` (progressive enhancement): read `data-product-slug`, selected `option[data-sku]`, quantity → POST add → re-render → optionally open the offcanvas (setting) + show a Bootstrap toast. If JS is unavailable, the form still posts to `storefront:add_to_cart`.
- Quantity steppers and Remove call PATCH/DELETE; coupon form calls the coupon endpoint; all re-render from the returned cart JSON.
- Cart page and drawer share one render function.

## Settings schema (`settings.py`)
`SCHEMA`/`DEFAULTS` (rendered on the admin plugin settings page):
- `open_drawer_on_add` (boolean, default `True`)
- `show_header_badge` (boolean, default `True`)
- `accent_color` (string, default `""` → theme primary)
- `free_shipping_threshold` (string, default `""`; if set, show a progress line)
- `empty_message` (string, default `"Your cart is empty."`)
- `checkout_label` (string, default `"Checkout"`)

## Theme / Bootstrap handling
- `head.html` loads Bootstrap CSS **then** `ajax_cart.css`, both before `main.css`, so the theme wins on shared class names (`.btn`, `.card`, `.badge`) while Bootstrap layout/utilities/offcanvas still work.
- `drawer.html` loads `bootstrap.bundle.min.js` then `ajax_cart.js` (both `defer`) and renders the offcanvas markup.
- `ajax_cart.css` keeps all selectors namespaced (`.ajax-cart*`) and derives colors from theme vars (`--primary`, `--surface`, `--border`) with `accent_color` override.

## Data flow
SSR page → `{% plugin_hook 'head'/'header_cart'/'body_end' %}` renders plugin partials (request-time, works immediately after enabling). `/cart/` → `spa_page(..., hook="cart_page")` sees the plugin claim → `cart_view` → `cart.html` → `{% plugin_hook 'cart_page' %}` → plugin page. All mutations go through `/api/v1/cart/*` and re-render client-side.

## Failure modes / edge cases
- Plugin disabled: `_plugin_claims` false → `/cart/` behaves exactly as today (SPA or default SSR); no hooks render.
- Plugin manager error in `_plugin_claims` → treated as not claimed (fail open to current behavior).
- JS disabled: add-to-cart still works via the SSR form; drawer/page show an empty state.
- Out-of-stock/unpublished/variant-required: the API returns an error → `ajax_cart.js` shows the message in the drawer (no silent failure).
- No session yet (first visit): API `resolve_cart(create=True)` creates the session/cart; the SSR page already has a session.
- Store resolution: API uses default store; SSR cart uses current store — fine for single-store setups (note as caveat).
- Drawer appears only on server-rendered pages; SPA pages (`/checkout/`, `/account/`, …) have no drawer (out of scope).
- Bootstrap CSS now loads on all storefront pages (before `main.css`); verify no visual regressions.

## Validation
- New `tests/test_plugins/test_ajax_cart_plugin.py`:
  - discovery/install/enable.
  - enabled: `/` contains Bootstrap CSS link, drawer markup, header cart button, `ajax_cart.js`.
  - disabled: none of the above; `/cart/` unchanged.
  - enabled + `STOREFRONT_SPA_ENABLED=True`: `/cart/` returns the SSR plugin page (plugin markup, **not** the SPA shell); disabled returns the SPA shell.
  - `STOREFRONT_SPA_ENABLED=False`: default cart page shows when disabled; plugin page when enabled.
  - plugin settings page renders and saves.
- Run: `pytest tests/test_plugins tests/test_storefront -q` then the full suite.
- Manual: `runserver`, enable AjaxCart in admin, hard-refresh product page (drawer + badge), add via AJAX (drawer opens, badge updates), `/cart/` shows the modern page, quantity/remove/coupon work; repeat with the Pacific theme; verify home/product/cart look unchanged except the drawer.

## Risks
- Bootstrap reboot/classes leaking into the storefront; mitigated by load order + namespaced plugin CSS (verify both themes).
- `_plugin_claims` adds a plugin-manager lookup per `/cart/` request (acceptable; guarded).
- Reusing the DRF API ties the AJAX cart to default-store resolution (single-store OK).
- Client-rendered cart page/drawer (JS-dependent); SSR add-to-cart remains the fallback.

## Out of scope
- Restyling the default/SPA cart.
- Making other SPA routes render the drawer.
- Plugin-owned JSON endpoints / changing `core/plugins/urls.py`.

## Open questions
- None blocking. (Confirm whether the drawer should also appear on SPA routes later, if desired.)
