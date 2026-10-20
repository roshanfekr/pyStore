# Requirements

**Status:** Draft (revision reflecting approved Vue theme, SQL Server, and
Widget Zones decisions; awaiting final review)

**Version:** 0.4

**Last updated:** 2026-10-20

**Authority:** Derived from `PROJECT_SCOPE.md` version 0.3. Where this document
and the revised scope differ, the conflict must be reported and resolved
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
  must not require editing core Vue components per language.
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
- FR-EXT-001: Widget Zones and plugin UI extension points are approved
  requirements. Plugins contribute Vue UI components through documented
  extension points across relevant storefront regions, including header
  regions, home page sections, product-details regions, category and product
  listing pages, cart and checkout, customer account pages, and footer
  regions. These examples are not an exhaustive final list. Contributions
  must support theme-compatible rendering, predictable ordering, visibility
  and permission rules where relevant, and defined fallback behavior.
- FR-EXT-002: Each Widget Zone must define a stable identifier, the Vue
  component or region where it appears, allowed contribution types, ordering,
  conflict-resolution rules, and fallback behavior. A plugin that provides no
  theme-specific component must use its default UI component where available.
  A missing or unavailable contribution must not break the storefront page.
- FR-EXT-003: The extension-point registry must be extensible so additional
  zones can be introduced without rewriting core Vue components or the active
  theme's core components. The final zone registry, naming conventions, and
  capabilities are architecture/design decisions.
- FR-EXT-004: Plugins may add menu items or submenus and may contribute links
  to supported Vue navigation areas. Contributions must support appropriate
  ordering, visibility, and permission checks and must not require editing
  core or theme components directly.

### 1.13 Vue Theme Layout, Components, and Overrides

These requirements extend `FR-THEME-001`, `FR-THEME-002`, and `FR-EXT-001`.
They govern storefront presentation only and do not authorize changes to
business logic, application data, APIs, or administrative behavior.

The storefront is an independent Vue/Vite application consuming the Django REST
Framework API. Requirements in this section define functional equivalents of
nopCommerce-style views and themes using Vue layouts, components, and assets.
They do not require Django server-side templates such as `.cshtml` or Django
HTML templates to control the Vue storefront. Server-side rendering is not
introduced by these requirements.

- **FR-THEME-LAYOUT-001: Global Theme Activation.** When an administrator
  activates a theme, every supported Vue storefront route must use that
  theme's root layout, page components, shared components, and static assets.
  Supported routes include, at minimum: home; product listing, category, and
  brand pages; product details; search results; cart; checkout and order
  confirmation; registration, login, and customer account pages; wishlist;
  compare; order history and order details; contact and informational/CMS
  pages; blog or news pages where provided; and other storefront routes
  supplied by core modules or installed plugins. Individual routes must not
  require separate theme selection. A supported route must not silently
  bypass the active theme; any route outside theme coverage must be explicitly
  documented.

- **FR-THEME-LAYOUT-002: Root Layout Component.** The system must support a
  theme-owned Vue root layout that defines the shared application shell and
  main rendering regions for storefront routes. It must support, where
  applicable: language/direction attributes; metadata and document title
  management; header; main content/router outlet; footer; global styles and
  scripts; and configurable layout regions and Widget Zones. Page components
  must be able to compose or be rendered within this root layout. The root
  layout must have a default fallback. The exact component name, composition
  mechanism, and routing integration must be documented during architecture.

- **FR-THEME-LAYOUT-003: Reusable Shared Components.** Themes must support
  reusable Vue components for shared storefront presentation, including:
  header and navigation; footer; metadata management; breadcrumbs; sidebar;
  one-, two-, and three-column layout regions; product cards; product images
  and galleries; pagination; cart components; customer account navigation;
  notifications and messages; and other reusable components. A shared
  component must be reusable by multiple page components. Updating a shared
  component in the active theme must affect every page that uses it without
  editing those pages individually. Shared components must follow the same
  resolution and fallback rules as page components.

- **FR-THEME-LAYOUT-004: Theme-Specific Page Components.** A theme must be
  able to provide its own Vue page component for an individual page type,
  including home, category/listing, product details, search, cart, checkout,
  customer account, wishlist, compare, order history, and informational pages.
  The system must select the appropriate page component automatically based on
  the current Vue route, route name, page type, or another documented
  application convention. A theme must be able to override one page component
  while continuing to use the theme's root layout and shared components, and
  while other page types continue to use default components.

- **FR-THEME-LAYOUT-005: Theme Component Resolution and Fallback.** Component
  resolution must be deterministic and consistent for root layouts, page
  components, shared components, layout variants, and plugin-contributed
  presentation. At minimum: (1) when the active theme provides the requested
  logical component, that component is used; (2) when it does not, the
  corresponding default theme/core component is used; (3) a missing optional
  theme component must not cause a storefront route to fail; (4) a theme must
  not be required to copy every default component; (5) overrides must not
  require modifying core application source files; and (6) the complete
  resolution order, fallback rules, and component naming contract must be
  documented during architecture and used consistently by all supported Vue
  routes and plugin UI.

- **FR-THEME-LAYOUT-006: Theme Package and Directory Organization.** Each
  theme must organize its files in a structured, maintainable package
  supporting Vue layouts, shared components, page-specific components, layout
  variants, plugin/extension components where applicable, CSS and JavaScript
  assets, images/icons/fonts, and theme configuration and metadata. The final
  directory layout, manifest fields, build/discovery integration, and
  component naming conventions must be defined during architecture after
  inspecting the existing Vue application. The structure must support a theme
  that overrides only a subset of components.

- **FR-THEME-LAYOUT-007: Theme-Aware Plugin Components.** The theme system
  must support storefront UI contributions from installed plugins through
  approved Widget Zones and extension points. A plugin may contribute reusable
  Vue UI components or widget content. A plugin may optionally provide a
  theme-specific component; when it does not, the system must use the plugin's
  default component where available. A plugin must not need to modify the
  active theme's core components or the Vue application's core components to
  contribute UI. Theme overrides and plugin-provided components must follow
  documented, deterministic resolution, ordering, and compatibility rules,
  including the interaction between a theme override and a plugin's
  theme-specific and default components.

- **FR-THEME-LAYOUT-008: Layout Variants.** Themes must support multiple Vue
  layout variants, including full-width, one-column, two-column with left
  sidebar, two-column with right sidebar, and three-column layouts. The
  applicable layout must be selectable by the relevant page or layout
  configuration according to documented project capabilities. Changing a
  route's layout must not require duplicating the entire page component. A
  missing theme-provided layout variant must fall back to a documented default
  layout variant.

- **FR-THEME-LAYOUT-009: Separation of Business Logic and Presentation.**
  Theme components are responsible for presentation only. They must consume
  data and services supplied by the application and must not independently
  implement pricing, discounts, tax, order processing, inventory, payment,
  permissions, or other business rules. Activating, deactivating, or switching
  a theme must not change business logic, persisted data, API behavior, or
  order-processing behavior.

- **FR-THEME-LAYOUT-010: Global Storefront Coverage and Traceability.** Theme
  coverage must be evaluated across all applicable Vue storefront routes,
  including routes registered by core modules and installed plugins. The
  project must maintain traceability between page types, Vue route or page
  component, root layout, shared components, layout variant, and relevant
  Widget Zones so that routes do not unintentionally bypass the active theme.
  The coverage record must identify any storefront route that is outside theme
  coverage. The administration interface has a separate layout/theme policy;
  activating a storefront theme must not unintentionally change the
  administration interface.

- **FR-THEME-LAYOUT-011: Theme Asset Resolution and Fallback.** CSS,
  JavaScript, images, icons, and fonts supplied by the active theme must be
  resolved and loaded consistently without editing core files. A theme may
  override only a subset of assets. Missing optional theme assets must fall
  back to the documented default asset or be treated as an explicitly optional
  asset; they must not produce broken storefront rendering or an application
  failure. Asset URL/versioning, loading order, and caching behavior must be
  documented during architecture.

- **FR-THEME-LAYOUT-012: Metadata Management.** The active theme must
  participate in managing document-level metadata for supported Vue routes,
  including the document title, applicable meta tags, language, and direction.
  Page and shared components must be able to supply route-specific metadata
  through a documented contract without each component manipulating global
  document state independently. Metadata changes must not alter business data
  or API behavior.

**Theme constraints:**

- Theme activation is an administrative action and must be subject to
  authorization. The mechanism for storing and applying the active theme is
  an architecture/design decision.
- Theme components and theme-supplied assets must be treated as untrusted
  presentation code from an installation and security perspective until the
  theme trust model is specified.
- The storefront remains client-side Vue. SSR must not be introduced unless it
  is separately evaluated and approved.
- Requirements in this section do not prescribe the final component names,
  resolution implementation, manifest schema, build integration, or layout
  variant algorithm.

## 2. Technical Requirements

These requirements record the approved technology direction from
`PROJECT_SCOPE.md` section 2. They are constraints on later design, not
architecture decisions.

- TR-STACK-001: The backend is implemented with Python and Django.
- TR-STACK-002: The backend exposes a Django REST Framework (DRF) API using an
  API-first approach.
- TR-STACK-003: The storefront frontend is a separate Vue.js application,
  built with Vite, that consumes the Django REST Framework API. Storefront
  themes are implemented with Vue layouts, components, and assets rather than
  server-rendered Django templates.
- TR-STACK-004: Bootstrap is the UI framework for the storefront and
  administration interface unless an approved exception is documented.
- TR-STACK-005: SQL Server is the initial database. PostgreSQL is a potential
  future database target, not the currently selected database. Migrating to
  PostgreSQL must not be assumed to require only a configuration change.
- TR-STACK-006: Storefront rendering remains client-side Vue. Server-side
  rendering must not be introduced unless it is separately evaluated and
  approved.

### 2.1 Database Requirements

- **TR-DB-001:** The initial database target is SQL Server. The compatible
  Django database backend and the minimum supported SQL Server version must be
  validated during architecture/design. The currently observed
  `mssql-django` integration is implementation evidence, not by itself a
  validated version-support decision.
- **TR-DB-002:** Django ORM is the preferred and approved ORM. SQLAlchemy or
  another ORM must not be introduced alongside Django ORM without explicit
  approval.
- **TR-DB-003:** Database-specific queries, raw SQL, schema assumptions, data
  types, and backend-specific behavior must be isolated behind documented
  boundaries. Portable Django ORM features must be used wherever practical so
  that a future PostgreSQL evaluation is feasible.
- **TR-DB-004:** All schema changes must use versioned Django migrations.
  Migrations must be testable against the supported SQL Server backend and
  must be reversible where practical. Any irreversible migration must be
  documented with its rationale and recovery approach.
- **TR-DB-005:** Data migrations must be explicit, validated, and safe to
  re-run where practical. They must define affected data, transformation
  rules, failure handling, and rollback or recovery strategy.
- **TR-DB-006:** Database portability must be verified through automated or
  repeatable checks that detect unsupported backend-specific queries and
  migration incompatibilities. A database switch requires separate evaluation
  of schema differences, data types, queries, migrations, and deployment
  configuration; it must not be claimed as configuration-only.

## 3. Non-Functional Requirements
- NFR-SEC-001: Authentication, authorization, validation, and safe handling of
  sensitive operations are enforced server-side. Secrets and sensitive data
  must not be exposed in logs, rendered UI, or client responses.
- NFR-EXT-001: Plugins and themes add capabilities without unnecessary core
  changes. Supported extensions must use documented contracts and extension
  points.
- NFR-MAINT-001: Clear module boundaries and documented contracts exist for
  core, plugins, themes, and feature modules.
- NFR-TEST-001: Automated tests cover critical business rules, workflows,
  authorization boundaries, theme component fallback, Widget Zone behavior, and
  storefront theme coverage.
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

### 4.1 Vue Theme Layout and Coverage

- **AC-THEME-LAYOUT-001** (`FR-THEME-LAYOUT-001`, `FR-THEME-002`): Activate a
  theme and open every Vue route classified as theme-covered in the coverage
  record. Each route uses the active theme's root layout, page component, and
  assets and displays an observable theme-specific marker. No supported route
  silently renders only the default theme.
- **AC-THEME-LAYOUT-002** (`FR-THEME-LAYOUT-002`, `FR-THEME-LAYOUT-012`): A
  theme with a custom Vue root layout renders its routes through that layout,
  including metadata/document title, language/direction attributes, header,
  main content/router outlet, footer, Widget Zones, and global assets.
- **AC-THEME-LAYOUT-003** (`FR-THEME-LAYOUT-003`): Change a shared header
  component in the active theme; every route that uses the shared component
  reflects the change without modifying individual page components.
- **AC-THEME-LAYOUT-004** (`FR-THEME-LAYOUT-004`): A theme can override the
  product-details page component and render it while continuing to use the
  theme's root layout and shared components, without copying the application.
- **AC-THEME-LAYOUT-005** (`FR-THEME-LAYOUT-004`, `FR-THEME-LAYOUT-005`): A
  theme can override the category page component while other routes continue
  to use default components, with no rendering failures.
- **AC-THEME-LAYOUT-006** (`FR-THEME-LAYOUT-005`): Remove an optional theme
  component. The affected route renders using the appropriate default
  component and does not fail.
- **AC-THEME-LAYOUT-007** (`FR-THEME-LAYOUT-005`): Installing a theme and
  overriding a component requires no modification to core application or
  default-theme source files.
- **AC-THEME-LAYOUT-008** (`FR-THEME-LAYOUT-009`): Switching themes leaves
  pricing, inventory, permissions, API responses, persisted data, and order
  processing behavior unchanged.
- **AC-THEME-LAYOUT-009** (`FR-THEME-LAYOUT-007`, `FR-EXT-001`): A plugin's Vue
  UI contribution renders through its defined Widget Zone on theme-covered
  routes.
- **AC-THEME-LAYOUT-010** (`FR-THEME-LAYOUT-007`, `FR-EXT-002`): A plugin with
  no theme-specific component continues to render through its default
  component, and an unavailable contribution does not break the page.
- **AC-THEME-LAYOUT-011** (`FR-THEME-LAYOUT-008`): Full-width, one-column,
  two-column-left, two-column-right, and three-column Vue layout variants
  render their expected regions using a single page component per page type.
- **AC-THEME-LAYOUT-012** (`FR-THEME-LAYOUT-010`): The coverage record lists
  every core and installed-plugin storefront route, its page type, Vue route
  or page component, root layout, shared components, layout variant, and
  Widget Zones. No route is unclassified.
- **AC-THEME-LAYOUT-013** (`FR-THEME-LAYOUT-010`): Activating or deactivating a
  storefront theme does not change the administration interface unless a
  separate administrative theme feature is explicitly applied.
- **AC-THEME-LAYOUT-014** (`FR-THEME-LAYOUT-006`, `FR-THEME-LAYOUT-011`): A
  theme can organize its Vue layouts, shared and page components, configuration
  and metadata, and CSS/JavaScript/image/font assets in the documented
  structure; theme-covered routes use the theme assets, and removing an
  optional theme component or asset produces the documented fallback rather
  than a broken page or application error.
- **AC-THEME-LAYOUT-015** (`FR-THEME-LAYOUT-012`): Route-specific document
  metadata is applied through the documented theme contract, and navigating
  between routes updates the title/language/direction metadata without
  inconsistent global state.

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
  a core Vue component edit.
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
  is the theme used by the supported storefront routes covered by section 4.1.
- **AC-EXT-001** (`FR-EXT-001`): An enabled plugin contributes a Vue UI
  component through a documented Widget Zone without editing core files or
  the active theme's core components.
- **AC-ZONE-001** (`FR-EXT-002`): A Widget Zone applies its documented ordering
  and fallback rules; a plugin without a theme-specific component renders its
  default component, and a missing contribution does not break the route.
- **AC-ZONE-002** (`FR-EXT-003`): A new Widget Zone can be registered and used
  by a theme/page component without rewriting unrelated core Vue components.
- **AC-EXT-003** (`FR-EXT-004`): A plugin can contribute a navigation item or
  link with documented ordering, visibility, and permission behavior without
  editing core or theme components.

### 4.3 Technical and Non-Functional Acceptance

- **AC-STACK-001** (`TR-STACK-001` through `TR-STACK-006`): Project and
  deployment configuration evidence identifies Django, DRF, Vue/Vite,
  Bootstrap, SQL Server as the initial database, and client-side Vue rendering
  without SSR; any deviation is recorded and approved as required by section 6.
- **AC-DB-001** (`TR-DB-001`): Architecture/design evidence identifies the
  compatible SQL Server Django backend, the minimum supported SQL Server
  version, and how that support will be validated.
- **AC-DB-002** (`TR-DB-002`): The implemented persistence layer uses Django
  ORM and contains no unapproved secondary ORM.
- **AC-DB-003** (`TR-DB-003`): Database-specific queries or schema assumptions
  are isolated and documented, and portable ORM usage is verified for the
  supported flows.
- **AC-DB-004** (`TR-DB-004`): Schema changes are represented by versioned
  migrations that can be applied on the supported SQL Server backend; every
  irreversible migration has a documented recovery approach.
- **AC-DB-005** (`TR-DB-005`): Data migrations are explicit and validated;
  where declared re-runnable, running them more than once does not corrupt or
  duplicate data.
- **AC-DB-006** (`TR-DB-006`): Repeatable checks detect unsupported
  backend-specific queries or migration incompatibilities, and no documentation
  claims that a PostgreSQL switch is configuration-only.
- **AC-SEC-001** (`NFR-SEC-001`): Unauthorized and invalid operations are
  rejected server-side, and no configured secret is present in rendered UI or
  API responses.
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
| FR-EXT-001 – FR-EXT-004 | PROJECT_SCOPE §6.2 – §7 | AC-EXT-001, AC-ZONE-001 – AC-ZONE-002, AC-EXT-003, AC-THEME-LAYOUT-009 |
| FR-THEME-LAYOUT-001 – FR-THEME-LAYOUT-012 | PROJECT_SCOPE §6 | AC-THEME-LAYOUT-001 – AC-THEME-LAYOUT-015 |
| TR-STACK-001 – TR-STACK-006 | PROJECT_SCOPE §2 | AC-STACK-001 |
| TR-DB-001 – TR-DB-006 | PROJECT_SCOPE §2, §8 | AC-DB-001 – AC-DB-006 |
| NFR-SEC-001 | PROJECT_SCOPE §8 | AC-SEC-001 |
| NFR-EXT-001, NFR-MAINT-001 | PROJECT_SCOPE §8 | AC-EXT-002 |
| NFR-TEST-001 | PROJECT_SCOPE §8 | AC-TEST-001 |
| NFR-API-001 | PROJECT_SCOPE §8 | AC-API-001 |
| NFR-REL-001 | PROJECT_SCOPE §8 | AC-REL-001 |
| NFR-PERF-001 | PROJECT_SCOPE §8 | AC-PERF-001 (open until targets approved) |
| NFR-ACC-001 | PROJECT_SCOPE §5, §8 | AC-ACC-001 |

### 5.2 Storefront Page Coverage Baseline

The approved decision is that the storefront is a separate Vue/Vite application
and themes control presentation through Vue layouts, components, and assets.
The current repository is still a hybrid: the Vue SPA owns the interactive
routes listed below, while several content routes are currently served by
Django templates. The table records both the approved target coverage and the
current implementation evidence so the gap is not hidden. Route names, page
component names, and the final resolution mechanism remain subject to
architecture/design and section 6.2.

| Page type | Approved target theme coverage | Current repository evidence | Theme/Widget Zone notes |
| --- | --- | --- | --- |
| Home | Vue route with theme home page component, root layout, shared components | Django `storefront/home.html`; not yet a Vue route | Theme page override and header/home/footer Widget Zones required. |
| Category / listing | Vue route with theme category page component | Django `storefront/category.html`; not yet a Vue route | Category/listing Widget Zones required. |
| Product details | Vue route with theme product page component | Django `storefront/product_detail.html`; not yet a Vue route | Product-details Widget Zones required. |
| Search results | Vue route with theme search page component | Django `storefront/search.html`; not yet a Vue route | Theme page override required. |
| Cart | Vue route with theme cart page component | Vue `CartView.vue` | Theme page override; cart Widget Zones required. |
| Checkout | Vue route with theme checkout page component | Vue `CheckoutView.vue` | Theme page override; checkout Widget Zones required. |
| Order history / details | Vue routes with theme account/order page components | Vue `AccountView.vue`, `OrderView.vue` | Theme page overrides; account/order Widget Zones required. |
| Registration / login | Vue routes with theme authentication page components | Vue `RegisterView.vue`, `LoginView.vue` | Theme page overrides required. |
| Account pages | Vue route with theme account page component | Vue `AccountView.vue` | Account navigation shared component required. |
| Wishlist | Vue route with theme wishlist page component | Vue `WishlistView.vue` | Theme page override required. |
| Compare | Vue route with theme compare page component | Vue `CompareView.vue` | Existing storefront page; theme page override required. |
| Contact / informational | Vue route with theme informational page component | Django `storefront/cms_page.html`; route not yet in Vue router | Theme page override and content Widget Zones required. |
| Blog / news | Vue routes with theme list/detail page components | Django blog templates; routes not yet in Vue router | Theme page overrides required where enabled. |
| Plugin-contributed storefront UI | Plugin Vue components rendered in approved Widget Zones | Current plugins provide Django hook templates such as `ajax_cart/*`, `flash_sale/*`, and `slider/*` | Migration to Vue plugin components and the approved Zone registry is required. |
| Administration | Separate admin interface and layout policy | Django admin templates | Storefront theme activation must not change the admin interface. |
| Robots / sitemap / autocomplete / suggestion endpoints | Non-page/API responses or explicitly documented theme coverage | Existing Django views/endpoints | Must be classified in the coverage record; not required to render a theme page unless specified. |

## 6. Conflicts, Deviations, and Unresolved Decisions

### 6.1 Scope Conflicts and Known Deviations

- **CF-001 — Database decision (resolved by approved decision).** SQL Server is
  the initial database and PostgreSQL is a potential future target, not the
  current database. The current repository's `mssql-django` configuration is
  consistent with the initial target. The compatible backend and minimum
  supported SQL Server version remain to be validated in architecture/design;
  see UD-013.
- **CF-002 — Vue theme decision vs. current hybrid implementation (resolved at
  requirement level).** The user approved a separate Vue/Vite storefront with
  Vue component/layout themes; Django server-side templates must not control
  the independent Vue storefront. The current repository still renders several
  content routes with Django templates and limits the Vue router to interactive
  routes. This is now an implementation gap recorded in section 5.2, not an
  unresolved requirements conflict. The gap must be addressed through later
  approved implementation work; this task does not modify application code.
- **CF-003 — Theme activation mechanism.** The scope says an administrator
  activates a theme; the current implementation resolves the active theme from
  the `ACTIVE_THEME` environment setting with a default. This is an
  implementation gap, not a change to the requirement. Persistence,
  per-store/global scope, and cache invalidation remain unresolved.
- **CF-004 — Widget Zones approved; registry pending.** Widget Zones and plugin
  UI extension points are approved requirements. The exact final zone registry,
  identifiers, naming conventions, and ordering contract remain architecture
  decisions; the examples in `PROJECT_SCOPE.md` section 7 are not an exhaustive
  final list.
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

- **UD-001 — Vue route coverage and migration.** Classify every storefront
  route as Vue/theme-covered or explicitly outside theme coverage, and define
  how current Django-rendered content routes are migrated to the approved Vue
  storefront without bypassing the active theme. Final route/component names
  remain architecture decisions.
- **UD-002 — Active-theme scope and persistence.** Decide whether the active
  theme is global, per store, or otherwise scoped; where activation is stored;
  how activation/deactivation takes effect; and how cached routes/assets are
  invalidated.
- **UD-003 — Theme component-resolution contract.** Define logical component
  names, namespacing, route/page mapping, and the exact precedence among active
  theme components, default theme/core components, plugin theme-specific
  components, and plugin default components. Apply the same rules to root
  layouts, page components, shared components, and layout variants.
- **UD-004 — Theme package and Vite integration.** Define the final theme
  directory structure, manifest schema, component/module format, discovery,
  build integration, static-asset organization, and asset URL/versioning
  policy.
- **UD-005 — Layout-variant selection.** Define how a route chooses full-width,
  one-, two-, or three-column Vue layout variants and how a missing theme
  variant falls back.
- **UD-006 — Plugin component contract.** Define how plugins declare Vue
  components and theme-specific variants, how compatibility is determined, and
  how ordering and conflicts with theme overrides are resolved across Widget
  Zones.
- **UD-007 — Widget Zone registry and coverage enforcement.** Define the final
  zone registry, identifiers, capabilities, ordering rules, and automated
  checks that prevent new core or plugin routes and zones from silently
  bypassing theme classification.
- **UD-008 — Administration theme policy.** Confirm the separate layout/theme
  policy for the admin interface and whether any administrative theming is in
  scope.
- **UD-009 — Currency conversion and payment policy.** Define exchange-rate
  source, conversion timing, rounding, display vs. charge currency, and
  behavior when a payment provider does not support the selected currency.
- **UD-010 — Translation fallback and content localization.** Define language
  fallback behavior, translated content ownership, and RTL handling for
  admin-authored content and generated storefront UI.
- **UD-011 — Theme trust and security model.** Define how Vue theme components
  and assets are validated, what capabilities theme authors have, and how
  untrusted theme code is isolated from secrets and business operations.
- **UD-012 — Performance targets.** Define measurable page/API performance and
  theme-rendering budgets before `AC-PERF-001` can be verified.
- **UD-013 — SQL Server backend and version support.** Validate the compatible
  Django SQL Server backend, supported SQL Server versions, driver/ODBC
  prerequisites, and connection/deployment requirements.
- **UD-014 — Database portability and migration strategy.** Define the
  portability checks, migration testing approach, irreversible-migration
  recovery rules, data-migration validation, and the conditions under which a
  future PostgreSQL evaluation may occur.

## 7. Approval Gate

This revision records the user-approved decisions on the Vue/Vite theme system,
SQL Server with Django ORM, and Widget Zones. It remains in Draft pending final
review and approval. It does not approve architecture, detailed design,
dependencies, database changes, migration work, or implementation. No
architecture/design or implementation work should begin until the user
explicitly approves the revised scope and requirements and authorizes the next
phase.
