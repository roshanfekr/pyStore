# Requirements

**Status:** Draft (revised requirements awaiting approval)

**Version:** 0.3

**Last updated:** 2026-10-20

**Authority:** Derived from the approved `PROJECT_SCOPE.md`. Where this document
and the approved scope differ, the conflict must be reported and resolved
rather than silently changing either document. See section 6.

**Normative language:** “Must” denotes a requirement; “should” denotes an
expected practice whose omission requires justification. Requirement and
acceptance-criteria identifiers are stable and must not be reused.

## 1. Functional Requirements

### 1.1 Admin & Access
- FR-ADMIN-001: Admin dashboard provides authenticated access to core
  management areas, including catalog, customers, orders, payments, shipping,
  discounts, store settings, plugins, themes, reports, and audit logs.
- FR-ADMIN-002: Role-based permission management controls access to admin
  functions and data operations. Authorization is enforced server-side, and
  unauthorized actions are rejected rather than hidden only in the UI.

### 1.2 Customer Accounts
- FR-CUST-001: Customers can register, authenticate, and manage their account.
  Authenticated customers can access their own account data only; another
  customer's data must not be exposed through account pages or APIs.

### 1.3 Catalog
- FR-CAT-001: Products support categories, brands, attributes, images, prices,
  and inventory. Attributes may represent options such as size, color, or
  material.
- FR-CAT-002: Products support variants via attribute combinations. Each
  combination may define its own price, SKU/product code, stock quantity,
  image or image set, and enabled/disabled state.
- FR-CAT-003: Storefront displays the relevant price and availability for the
  selected combination. Selection changes must update the displayed price,
  availability, and applicable image without requiring a page reload.
- FR-CAT-004: The selected combination is validated when adding to the cart and
  when placing the order. Invalid, disabled, or unavailable combinations must
  be rejected with a clear error; the server must revalidate rather than trust
  client-side selection.
- FR-CAT-005: Catalog supports search, filtering, sorting, and browsing.

### 1.4 Cart & Checkout
- FR-CART-001: Customers can manage a shopping cart: add items, change
  quantities, remove items, and view item lines and totals.
- FR-CHK-001: Checkout process completes an order with the selected payment
  and shipping methods, validates required customer and order data, and
  produces an order confirmation.

### 1.5 Orders
- FR-ORD-001: Orders track status and customer history. Authenticated customers
  can view their own order history and order details; orders belonging to
  another customer must not be exposed.

### 1.6 Payments & Shipping
- FR-PAY-001: Payment methods are configurable. Only enabled methods are
  offered at checkout, and the outcome of a payment attempt is recorded against
  the order.
- FR-SHIP-001: Shipping methods are configurable. Only enabled methods are
  offered at checkout, and the selected method is recorded against the order.

### 1.7 Discounts & Promotions
- FR-DISC-001: Discounts, coupons, and promotions are supported and applied
  according to their configured eligibility, scope, and validity rules.

### 1.8 Store Settings, Localization & Currency
- FR-SET-001: Store settings, currency, and tax configuration are configurable
  and applied consistently to storefront display and order processing.
- FR-I18N-001: The storefront supports multiple configured languages.
  Customers can select a language, and user-visible content and interface text
  are presented in the active language where a translation is available.
- FR-I18N-002: Right-to-left (RTL) languages are supported. When an RTL
  language is active, the document direction and applicable layout mirroring
  must be applied without breaking navigation, forms, or content.
- FR-I18N-003: Locale-dependent presentation, including translated labels and
  language-appropriate formatting, must be driven by the active language and
  must not require editing core templates per language.
- FR-CUR-001: Multiple currencies can be configured. Prices are displayed in
  the active currency using its configured symbol and decimal precision.
- FR-CUR-002: Multi-currency support extends to payment and order processing.
  Checkout, payment, and the resulting order must use the selected currency;
  the order must retain the currency and payable amount. A payment method that
  cannot support the selected currency must fail clearly rather than silently
  charging a different currency.
- FR-CUR-003: Currency selection and display must be consistent across
  catalog, cart, checkout, order history, and informational pages. Currency
  conversion, rounding, and exchange-rate policy are unresolved and must be
  specified before implementation (see section 6.2).

### 1.9 Reviews & Ratings
- FR-REV-001: Product reviews and ratings can be submitted and displayed,
  subject to the configured customer and moderation rules.

### 1.10 Notifications
- FR-NOTIF-001: Notification support covers relevant storefront and order
  events, with notifications delivered through configured channels and visible
  to the intended recipient.

### 1.11 Reports & Audit
- FR-REP-001: Reports and audit logs provide authorized administrators with
  operational reporting and a record of security- or business-relevant actions.

### 1.12 Plugins & Themes
- FR-PLUG-001: Plugin installation and management are supported. Plugins can
  be discovered, installed, enabled, disabled, and removed through the
  established plugin lifecycle without requiring manual edits to core files.
- FR-THEME-001: Theme installation, configuration, activation, and
  deactivation are supported. Theme activation is an authorized administrative
  action. A theme can expose configurable settings, and the configured values
  are applied to that theme's presentation.
- FR-THEME-002: The active theme applies consistently across supported
  storefront pages as detailed in section 1.13.
- FR-EXT-001: Plugins contribute UI via defined extension points. A plugin's
  presentation may be theme-aware, with a default presentation fallback when a
  theme-specific implementation is unavailable. Plugins must not need to
  modify core files or the active theme's core templates to contribute UI.

### 1.13 Theme Layout and Template Override

These requirements extend `FR-THEME-001`, `FR-THEME-002`, and `FR-EXT-001`.
They govern storefront presentation only and do not authorize changes to
business logic, application data, APIs, or administrative behavior.

- **FR-THEME-LAYOUT-001: Global Theme Activation.** When an administrator
  activates a theme, every supported storefront page must render using that
  theme's layouts, page templates, reusable partials, and static assets. This
  includes, at minimum: home; product listing, category, and brand pages;
  product details; search results; cart; checkout and order confirmation;
  registration, login, and customer account pages; wishlist; compare; order
  history and order details; contact and informational/CMS pages; blog or
  news pages where provided; and other storefront pages supplied by core
  modules or installed plugins. Individual pages must not require separate
  theme selection. A storefront page that cannot use theme templates (for
  example, a page rendered by a client-side application shell) must either
  consume an equivalent presentation contract from the active theme or be
  explicitly documented as outside the theme-template scope. No supported
  page may silently bypass the active theme.

- **FR-THEME-LAYOUT-002: Root Layout Template.** The system must support a
  theme-owned root layout that defines the shared HTML document structure and
  main rendering areas for storefront pages. It must support, where
  applicable: document type and language/direction attributes; the head
  section; header; main content area; footer; global styles and scripts; and
  configurable layout regions and widget/extension zones. Page templates must
  be able to inherit from or compose this root layout. The root layout must
  have a default fallback. The exact template name and inheritance mechanism
  must follow the project's existing Django conventions and be documented
  during architecture.

- **FR-THEME-LAYOUT-003: Reusable Template Partials.** Themes must support
  reusable partials for shared storefront presentation, including functional
  equivalents of: head and metadata; header and navigation; footer;
  breadcrumbs; sidebar; one-, two-, and three-column layout regions; product
  cards; product images and galleries; pagination; cart components; customer
  account navigation; notifications and messages; and other reusable
  components. A partial must be reusable by multiple page templates. Updating
  a shared partial in the active theme must affect every page that uses it
  without editing those pages individually. Partials must follow the same
  fallback rules as page templates.

- **FR-THEME-LAYOUT-004: Page-Specific Templates.** A theme must be able to
  provide its own template for an individual page type, including home,
  category/listing, product details, search, cart, checkout, customer
  account, wishlist, compare, order history, and informational pages. The
  system must select the appropriate page template automatically based on
  the current route, view, page type, or another documented application
  convention. A theme must be able to override one page template while
  continuing to use the theme's root layout and shared partials, and while
  other page types continue to use default templates.

- **FR-THEME-LAYOUT-005: Theme Template Resolution and Fallback.** Template
  resolution must be deterministic and consistent for root layouts, page
  templates, reusable partials, and plugin-contributed presentation. At
  minimum: (1) when the active theme provides the requested logical template,
  that template is used; (2) when it does not, the corresponding default
  core/application template is used; (3) a missing optional theme template or
  partial must not cause a storefront page to fail; (4) a theme must not be
  required to copy every core template; (5) overrides must not require
  modifying core application source files; and (6) the complete resolution
  order and naming rules must be documented during architecture and used
  consistently by all storefront rendering paths.

- **FR-THEME-LAYOUT-006: Theme Directory Structure.** Each theme must be able
  to organize its files in a structured, maintainable directory supporting
  layout templates, shared partials, page-specific templates, CSS and
  JavaScript assets, images/icons/fonts, theme configuration and metadata,
  and optional theme-specific component templates. The final directory
  layout, manifest fields, and template naming conventions must be defined
  during architecture after inspecting the existing repository. The
  structure must support a theme that overrides only a subset of templates.

- **FR-THEME-LAYOUT-007: Theme-Aware Plugins.** The theme system must support
  storefront UI contributions from installed plugins through defined
  extension points and widget zones. A plugin may contribute reusable UI
  components, templates, or widget content. A plugin may optionally provide
  a theme-specific presentation template; when it does not, the system must
  use the plugin's default presentation template where available. A plugin
  must not need to modify the active theme's core templates to contribute UI.
  Theme overrides and plugin-provided templates must follow documented,
  deterministic resolution and compatibility rules, including the
  interaction between a theme override and a plugin's theme-specific and
  default templates. Extension-point identifiers and capabilities remain
  subject to their own approved specification; this requirement does not
  approve the proposed widget-zone catalog in `PROJECT_SCOPE.md` section 7.

- **FR-THEME-LAYOUT-008: Layout Variants.** Themes must support multiple page
  layouts, including full-width, one-column, two-column with left sidebar,
  two-column with right sidebar, and three-column layouts. The applicable
  layout must be selectable by the relevant page or layout configuration
  according to documented project capabilities. Changing a page's layout
  must not require duplicating the entire page template. A missing
  theme-provided layout variant must fall back to a documented default.

- **FR-THEME-LAYOUT-009: Separation of Business Logic and Presentation.**
  Theme templates are responsible for presentation only. They must consume
  data and context supplied by the application and must not independently
  implement pricing, discounts, tax, order processing, inventory, payment,
  permissions, or other business rules. Activating, deactivating, or
  switching a theme must not change business logic, persisted data, API
  behavior, or order-processing behavior.

- **FR-THEME-LAYOUT-010: Global Storefront Coverage and Traceability.** Theme
  coverage must be evaluated across all applicable storefront routes,
  including routes registered by core modules and installed plugins. The
  project must maintain traceability between page types, their rendering
  templates, shared layouts/partials, and relevant extension points so that
  pages do not unintentionally bypass the active theme. The coverage record
  must identify any storefront route that is outside theme-template scope.
  The administration interface has a separate layout/theme policy; activating
  a storefront theme must not unintentionally change the administration
  interface.

- **FR-THEME-LAYOUT-011: Theme Asset Resolution and Fallback.** CSS,
  JavaScript, images, icons, and fonts supplied by the active theme must be
  resolved and referenced consistently without editing core files. A theme may
  override only a subset of assets. Missing optional theme assets must fall
  back to the documented default asset or be treated as an explicitly optional
  asset; they must not produce broken storefront rendering or a server error.
  Asset URL/versioning and caching behavior must be documented during
  architecture.

**Theme constraints:**

- Theme activation is an administrative action and must be subject to
  authorization. The mechanism for storing and applying the active theme is
  an architecture/design decision.
- Theme templates and theme-supplied assets must be treated as untrusted
  presentation code from an installation and security perspective until the
  theme trust model is specified.
- Requirements in this section do not prescribe the final template names,
  loader implementation, manifest schema, or resolution algorithm.

## 2. Technical Requirements

These requirements record the approved technology direction from
`PROJECT_SCOPE.md` section 2. They are constraints on later design, not
architecture decisions.

- TR-STACK-001: The backend is implemented with Python and Django.
- TR-STACK-002: The backend exposes a Django REST Framework (DRF) API using an
  API-first approach.
- TR-STACK-003: The frontend direction is a standalone Vue.js application
  consuming the backend API. Its relationship to server-rendered theme
  templates is unresolved; see CF-002 in section 6.1.
- TR-STACK-004: Bootstrap is the UI framework for the storefront and
  administration interface unless an approved exception is documented.
- TR-STACK-005: PostgreSQL is the approved database. A deployment or settings
  configuration using a different database engine is a documented deviation
  requiring approval; it must not silently replace this decision. The current
  repository's SQL Server configuration is recorded in section 6.1 and is not
  approval to change the PostgreSQL decision.

## 3. Non-Functional Requirements
- NFR-SEC-001: Authentication, authorization, validation, and safe handling of
  sensitive operations are enforced server-side. Secrets and sensitive data
  must not be exposed in logs, templates, or client responses.
- NFR-EXT-001: Plugins and themes add capabilities without unnecessary core
  changes. Supported extensions must use documented contracts and extension
  points.
- NFR-MAINT-001: Clear module boundaries and documented contracts exist for
  core, plugins, themes, and feature modules.
- NFR-TEST-001: Automated tests cover critical business rules, workflows,
  authorization boundaries, template fallback, and theme coverage.
- NFR-API-001: APIs are documented and versionable, with stable request and
  response contracts.
- NFR-REL-001: Order, inventory, payment, and other state transitions are
  consistent and failure-safe; repeated or partial operations must not leave
  contradictory state.
- NFR-PERF-001: Page and API behavior is responsive under expected workloads.
  Measurable performance targets remain to be defined in a later approved
  specification.
- NFR-ACC-001: Interfaces are usable across supported devices and interaction
  methods, including keyboard navigation and accessible form feedback.

## 4. Acceptance Criteria

Detailed feature-level acceptance criteria may later move into `features/*`,
but the criteria below are binding for requirement verification. Every
acceptance criterion must be traceable to at least one requirement in section
5.

### 4.1 Theme Layout and Coverage

- **AC-THEME-LAYOUT-001** (`FR-THEME-LAYOUT-001`, `FR-THEME-002`): Activate a
  theme and render every route classified as theme-rendered in the coverage
  record. Each page uses the active theme's layout and assets and displays an
  observable theme-specific marker. No supported page silently renders only
  the default theme.
- **AC-THEME-LAYOUT-002** (`FR-THEME-LAYOUT-002`): A theme with a custom root
  layout renders pages that inherit from or compose it, including the
  document structure, language/direction attributes, header, main content
  area, footer, and global assets.
- **AC-THEME-LAYOUT-003** (`FR-THEME-LAYOUT-003`): Change a shared header
  partial in the active theme; every page that includes the partial reflects
  the change without modifying individual page templates.
- **AC-THEME-LAYOUT-004** (`FR-THEME-LAYOUT-004`): A theme can override the
  product-details template and render the override while continuing to use the
  theme's root layout and shared partials, without copying the application.
- **AC-THEME-LAYOUT-005** (`FR-THEME-LAYOUT-004`, `FR-THEME-LAYOUT-005`): A
  theme can override the category page while other page types continue to use
  default templates, with no rendering failures.
- **AC-THEME-LAYOUT-006** (`FR-THEME-LAYOUT-005`): Remove an optional theme
  template or partial. The affected page renders using the appropriate default
  template and does not fail.
- **AC-THEME-LAYOUT-007** (`FR-THEME-LAYOUT-005`): Installing a theme and
  overriding a template requires no modification to core application source
  files.
- **AC-THEME-LAYOUT-008** (`FR-THEME-LAYOUT-009`): Switching themes leaves
  pricing, inventory, permissions, API responses, persisted data, and order
  processing behavior unchanged.
- **AC-THEME-LAYOUT-009** (`FR-THEME-LAYOUT-007`, `FR-EXT-001`): A plugin's UI
  contribution renders through its defined extension point on theme-rendered
  pages.
- **AC-THEME-LAYOUT-010** (`FR-THEME-LAYOUT-007`): A plugin with no
  theme-specific template continues to render through its default template.
- **AC-THEME-LAYOUT-011** (`FR-THEME-LAYOUT-008`): Full-width, one-column,
  two-column-left, two-column-right, and three-column layouts render their
  expected regions using a single page template per page type.
- **AC-THEME-LAYOUT-012** (`FR-THEME-LAYOUT-010`): The coverage record lists
  every core and installed-plugin storefront route, its page type, rendering
  template, root layout, shared partials, and extension points. No route is
  unclassified.
- **AC-THEME-LAYOUT-013** (`FR-THEME-LAYOUT-010`): Activating or deactivating a
  storefront theme does not change the administration interface unless a
  separate administrative theme feature is explicitly applied.
- **AC-THEME-LAYOUT-014** (`FR-THEME-LAYOUT-011`): Theme CSS, JavaScript, and
  image assets are used by theme-rendered pages; removing an optional theme
  asset produces the documented fallback rather than a broken page or server
  error.

### 4.2 Core Functional Acceptance

- **AC-ADMIN-001** (`FR-ADMIN-001`): An authorized administrator can reach the
  documented management areas from the admin dashboard.
- **AC-ADMIN-002** (`FR-ADMIN-002`): A user without the required permission is
  denied an admin operation through both the UI and direct request.
- **AC-CUST-001** (`FR-CUST-001`): A customer can register, authenticate,
  update their account, and cannot access another customer's account data.
- **AC-CAT-001** (`FR-CAT-001`): Products display categories, brands,
  attributes, images, prices, and inventory where configured.
- **AC-CAT-002** (`FR-CAT-002`): A product with multiple attribute combinations
  exposes each combination's configured price, SKU, stock, image set, and
  enabled state.
- **AC-CAT-003** (`FR-CAT-003`): Selecting a combination updates the displayed
  price, availability, and image to that combination's values.
- **AC-CAT-004** (`FR-CAT-004`): Adding an invalid, disabled, or unavailable
  combination to the cart or placing an order with it is rejected by the
  server.
- **AC-CAT-005** (`FR-CAT-005`): Search, filtering, sorting, and catalog
  browsing return results consistent with their criteria.
- **AC-CART-001** (`FR-CART-001`): A customer can add, update, and remove cart
  items and sees correspondingly updated lines and totals.
- **AC-CHK-001** (`FR-CHK-001`): A valid checkout completes with selected
  payment and shipping methods and produces an order confirmation; invalid
  checkout data is rejected without creating an order.
- **AC-ORD-001** (`FR-ORD-001`): Order status and history are recorded, and a
  customer can view only their own order history and details.
- **AC-PAY-001** (`FR-PAY-001`): Only enabled payment methods are offered, and
  a payment outcome is recorded against the order.
- **AC-SHIP-001** (`FR-SHIP-001`): Only enabled shipping methods are offered,
  and the selected method is recorded against the order.
- **AC-DISC-001** (`FR-DISC-001`): A valid discount, coupon, or promotion is
  applied according to its configuration; an ineligible one is rejected.
- **AC-SET-001** (`FR-SET-001`): Configured store settings, currency, and tax
  settings affect storefront display and order processing as configured.
- **AC-I18N-001** (`FR-I18N-001`, `FR-I18N-003`): Switching the active language
  changes available translated content and interface labels without requiring
  a core template edit.
- **AC-I18N-002** (`FR-I18N-002`): Selecting an RTL language sets RTL document
  direction and produces a usable mirrored layout without overlapping or
  inaccessible controls.
- **AC-CUR-001** (`FR-CUR-001`, `FR-CUR-003`): Prices display the active
  currency's symbol and decimal precision consistently across storefront
  pages.
- **AC-CUR-002** (`FR-CUR-002`, `FR-CUR-003`): Checkout, payment, and the
  resulting order use and retain the selected currency and payable amount; an
  unsupported currency/payment combination fails clearly.
- **AC-REV-001** (`FR-REV-001`): A permitted customer can submit a review and
  rating, and accepted reviews are displayed according to configured rules.
- **AC-NOTIF-001** (`FR-NOTIF-001`): A qualifying event produces a notification
  to the intended recipient through the configured channel.
- **AC-REP-001** (`FR-REP-001`): An authorized administrator can view the
  documented reports and audit records, and a relevant action is recorded.
- **AC-PLUG-001** (`FR-PLUG-001`): A plugin can be installed, enabled,
  disabled, and removed through the supported lifecycle without core-file
  edits.
- **AC-THEME-001** (`FR-THEME-001`): An authorized administrator can install,
  configure, activate, and deactivate a theme; configured settings affect that
  theme's presentation.
- **AC-THEME-002** (`FR-THEME-002`, `FR-THEME-LAYOUT-001`): The activated theme
  is the theme used by the supported storefront pages covered by section 4.1.
- **AC-EXT-001** (`FR-EXT-001`): An enabled plugin contributes UI through a
  documented extension point without editing core files or the active theme's
  core templates.

### 4.3 Technical and Non-Functional Acceptance

- **AC-STACK-001** (`TR-STACK-001` through `TR-STACK-005`): Project and
  deployment configuration evidence identifies Django, DRF, Vue, Bootstrap,
  and the approved database decision; any deviation is recorded and approved
  as required by section 6.
- **AC-SEC-001** (`NFR-SEC-001`): Unauthorized and invalid operations are
  rejected server-side, and no configured secret is present in rendered
  templates or API responses.
- **AC-EXT-002** (`NFR-EXT-001`, `NFR-MAINT-001`): A supported plugin or theme
  can be added through documented contracts without modifying core application
  source files.
- **AC-TEST-001** (`NFR-TEST-001`): Automated tests exist for the critical
  behaviors referenced by section 4.2 and for the theme fallback/coverage
  behaviors referenced by section 4.1.
- **AC-API-001** (`NFR-API-001`): Documented API contracts match observed
  requests and responses for the verified flows.
- **AC-REL-001** (`NFR-REL-001`): Failure and retry scenarios do not produce
  contradictory order, inventory, payment, or other persisted state.
- **AC-PERF-001** (`NFR-PERF-001`): Storefront pages and APIs meet the
  measurable targets once those targets are approved; until then, this
  criterion remains open.
- **AC-ACC-001** (`NFR-ACC-001`): Primary storefront and admin flows are
  operable by keyboard on supported viewport sizes.

## 5. Traceability and Storefront Coverage

### 5.1 Requirement Traceability

| Requirement group | Source | Acceptance criteria |
| --- | --- | --- |
| FR-ADMIN-001 – FR-ADMIN-002 | PROJECT_SCOPE §3, §6 | AC-ADMIN-001 – AC-ADMIN-002 |
| FR-CUST-001 | PROJECT_SCOPE §3 | AC-CUST-001 |
| FR-CAT-001 – FR-CAT-005 | PROJECT_SCOPE §3 – §4 | AC-CAT-001 – AC-CAT-005 |
| FR-CART-001, FR-CHK-001 | PROJECT_SCOPE §3 | AC-CART-001, AC-CHK-001 |
| FR-ORD-001 | PROJECT_SCOPE §3 | AC-ORD-001 |
| FR-PAY-001, FR-SHIP-001 | PROJECT_SCOPE §3 | AC-PAY-001, AC-SHIP-001 |
| FR-DISC-001 | PROJECT_SCOPE §3 | AC-DISC-001 |
| FR-SET-001 | PROJECT_SCOPE §3 | AC-SET-001 |
| FR-I18N-001 – FR-I18N-003 | Project localization decision; see section 6 | AC-I18N-001 – AC-I18N-002 |
| FR-CUR-001 – FR-CUR-003 | Project multi-currency decision; see section 6 | AC-CUR-001 – AC-CUR-002 |
| FR-REV-001 | PROJECT_SCOPE §3 | AC-REV-001 |
| FR-NOTIF-001 | PROJECT_SCOPE §3 | AC-NOTIF-001 |
| FR-REP-001 | PROJECT_SCOPE §3 | AC-REP-001 |
| FR-PLUG-001 | PROJECT_SCOPE §3, §6.2 | AC-PLUG-001 |
| FR-THEME-001, FR-THEME-002 | PROJECT_SCOPE §3, §6 | AC-THEME-001, AC-THEME-002 |
| FR-EXT-001 | PROJECT_SCOPE §6.2 – §7 | AC-EXT-001, AC-THEME-LAYOUT-009 |
| FR-THEME-LAYOUT-001 – FR-THEME-LAYOUT-011 | Theme layout extension; `PROJECT_SCOPE.md` §6 | AC-THEME-LAYOUT-001 – AC-THEME-LAYOUT-014 |
| TR-STACK-001 – TR-STACK-005 | PROJECT_SCOPE §2 | AC-STACK-001 |
| NFR-SEC-001 | PROJECT_SCOPE §8 | AC-SEC-001 |
| NFR-EXT-001, NFR-MAINT-001 | PROJECT_SCOPE §8 | AC-EXT-002 |
| NFR-TEST-001 | PROJECT_SCOPE §8 | AC-TEST-001 |
| NFR-API-001 | PROJECT_SCOPE §8 | AC-API-001 |
| NFR-REL-001 | PROJECT_SCOPE §8 | AC-REL-001 |
| NFR-PERF-001 | PROJECT_SCOPE §8 | AC-PERF-001 (open until targets approved) |
| NFR-ACC-001 | PROJECT_SCOPE §5, §8 | AC-ACC-001 |

### 5.2 Storefront Page Coverage Baseline

The following table is evidence from the current repository, provided to
support traceability. Route names, template names, and rendering mechanisms
remain subject to architecture/design and the unresolved decisions in section
6.2. A page marked as SPA-conditional has a server-rendered fallback but may
bypass Django templates when the SPA is enabled.

| Page type | Current route(s) | Current rendering evidence | Theme/extension notes |
| --- | --- | --- | --- |
| Home | `/` | `storefront/home.html` | Theme can override page template and shared partials; plugin hook `home_middle` exists. |
| Category / listing | `/category/<slug>/` | `storefront/category.html` | Theme page override required; category extension points proposed in scope. |
| Product details | `/product/<slug>/` | `storefront/product_detail.html` | Theme page override required; product extension points proposed in scope. |
| Search results | `/search/` | `storefront/search.html` | Theme page override required. |
| Cart | `/cart/` | `storefront/cart.html` | SPA-conditional; plugin hook `cart_page` can claim server rendering. |
| Checkout | `/checkout/` | `storefront/checkout.html` | SPA-conditional; order confirmation route exists. |
| Order history / details | `/account/`, `/orders/<number>/` | `storefront/account.html`, `storefront/order_detail.html` | SPA-conditional; account/order theme templates required. |
| Registration / login | `/register/`, `/login/` | `storefront/register.html`, `storefront/login.html` | SPA-conditional. |
| Account pages | `/account/` | `storefront/account.html` | SPA-conditional; account navigation partial required. |
| Wishlist | `/wishlist/` | `storefront/wishlist.html` | SPA-conditional. |
| Compare | `/compare/` | `storefront/compare.html` | SPA-conditional; included because it is an existing storefront page. |
| Contact / informational | `/<slug>/` | `storefront/cms_page.html` | CMS page; theme page/partial coverage required. |
| Blog / news | `/blog/`, `/blog/<slug>/` | `storefront/blog_list.html`, `storefront/blog_detail.html` | Theme page overrides required where the feature is enabled. |
| Plugin-contributed storefront UI | Extension points rendered by `plugin_hook` | Plugin templates such as `ajax_cart/*`, `flash_sale/*`, `slider/*` | Current hooks include `head`, `header_cart`, `body_end`, `home_middle`, and `cart_page`; widget-zone catalog is not approved. |
| Administration | `/admin/` (and admin-specific routes) | Admin templates | Separate layout/theme policy; storefront activation must not change it. |
| Robots / sitemap / autocomplete / suggestion endpoints | `/robots.txt`, `/sitemap.xml`, `/search/autocomplete/`, `/search/suggest/` | Non-page or partial responses | Must be classified in the coverage record; not required to render theme HTML unless specified. |

## 6. Conflicts, Deviations, and Unresolved Decisions

### 6.1 Scope Conflicts and Known Deviations

- **CF-001 — Database decision vs. current configuration.** `PROJECT_SCOPE.md`
  section 2 approves PostgreSQL, while the current repository's default
  settings and README identify SQL Server (`mssql-django`). This requirements
  revision retains PostgreSQL as the approved decision per the task. The
  implementation discrepancy must be reconciled or the database change must
  be explicitly approved; it must not be resolved silently in either
  direction.
- **CF-002 — Standalone Vue direction vs. template-driven storefront.**
  `PROJECT_SCOPE.md` section 2 specifies a standalone Vue.js frontend consuming
  the API, while the current repository is a hybrid of server-rendered Django
  templates and a Vue SPA, and the requested theme requirements assume
  theme-owned HTML layouts and page templates. The coexistence model, the
  theme-control boundary for SPA-rendered routes, and whether both rendering
  paths are in scope require explicit approval before architecture. This
  document does not choose between them.
- **CF-003 — Theme activation mechanism.** The scope says an administrator
  activates a theme; the current implementation resolves the active theme from
  the `ACTIVE_THEME` environment setting with a default. This is an
  implementation gap, not a change to the requirement. Persistence,
  per-store/global scope, and cache invalidation remain unresolved.
- **CF-004 — Widget-zone proposal status.** `PROJECT_SCOPE.md` section 7 is
  marked as a proposal awaiting explicit approval. `FR-EXT-001`,
  `FR-THEME-LAYOUT-007`, and the acceptance criteria refer to defined extension
  points and do not approve the proposed widget-zone groups or identifiers.
- **CF-005 — Localization and currency detail.** Multilingual, RTL, and
  multi-currency display/payment are treated as approved project requirements
  for this revision, but `PROJECT_SCOPE.md` does not fully specify translation
  fallback, currency conversion, rounding, or payment-provider currency
  support. These gaps must be resolved without silently narrowing or expanding
  the approved capability.
- **CF-006 — Performance targets.** `PROJECT_SCOPE.md` section 8 requires
  responsive performance but defers measurable targets. `NFR-PERF-001` and
  `AC-PERF-001` remain open until targets are approved.

### 6.2 Unresolved Decisions for Architecture/Design

These decisions are not approved requirements. They must be resolved and,
where they affect scope, explicitly approved.

- **UD-001 — Storefront rendering model.** Confirm the relationship between
  the standalone Vue application and server-rendered theme templates, and
  classify which storefront routes are theme-rendered, SPA-rendered with a
  theme presentation contract, or outside theme-template scope.
- **UD-002 — Active-theme scope and persistence.** Decide whether the active
  theme is global, per store, or otherwise scoped; where activation is stored;
  how activation/deactivation takes effect; and how cached pages/assets are
  invalidated.
- **UD-003 — Template naming and resolution order.** Define logical template
  names, namespacing, and the exact precedence among active theme, default
  core template, plugin theme-specific template, and plugin default template.
  Apply the same rules to root layouts, page templates, and partials.
- **UD-004 — Theme directory and manifest schema.** Define the final
  directory structure, metadata fields, static-asset organization, optional
  template subsets, and asset URL/versioning policy.
- **UD-005 — Layout-variant selection.** Define how a page chooses full-width,
  one-, two-, or three-column layouts and how a missing theme variant falls
  back.
- **UD-006 — Plugin theme-specific presentation contract.** Define how plugins
  declare theme-specific templates, how compatibility is determined, and how
  conflicts with theme overrides are resolved.
- **UD-007 — Coverage enforcement.** Define the route registry or equivalent
  mechanism and automated checks that prevent new core or plugin routes from
  silently bypassing theme classification.
- **UD-008 — Administration theme policy.** Confirm that the admin interface
  has a separate layout/theme policy and whether any administrative theming is
  in scope.
- **UD-009 — Currency conversion and payment policy.** Define exchange-rate
  source, conversion timing, rounding, display vs. charge currency, and
  behavior when a payment provider does not support the selected currency.
- **UD-010 — Translation fallback and content localization.** Define language
  fallback behavior, translated content ownership, and RTL handling for
  admin-authored content and generated storefront UI.
- **UD-011 — Theme trust and security model.** Define how theme templates and
  assets are validated, what capabilities theme authors have, and how
  untrusted theme code is isolated from secrets and business operations.
- **UD-012 — Performance targets.** Define measurable page/API performance and
  theme-rendering budgets before `AC-PERF-001` can be verified.

## 7. Approval Gate

This revision is a requirements proposal. It does not approve architecture,
detailed design, dependencies, database changes, or implementation. No
architecture/design or implementation work should begin until the user
explicitly approves these requirements and resolves the scope conflicts in
section 6.1 that require a decision.
