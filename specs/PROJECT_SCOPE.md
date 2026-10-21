# Project Scope --- Plugin-Based E-commerce Platform

**Document:** `specs/PROJECT_SCOPE.md`\
**Version:** 0.8 (draft adding four newly identified capability directions —
plugin-defined scheduled tasks, an extensible application event/consumer
mechanism, configurable CAPTCHA with Google reCAPTCHA support, and
SMS-compatible registration — to the previously recorded decisions,
including the proposed V1 performance baseline)\
**Status:** Draft pending final review. The core scope remains approved; this
revision records the user-approved decisions on the Vue/Vite theme system,
SQL Server with Django ORM, Widget Zones, the initial Django Admin interface,
multi-currency pricing, multilingual/RTL support, the deferral of refunds and
automatic currency conversion to a future release, and the rule that payment
providers must support the order currency. It additionally records the
approved direction to adopt proposed, provisional V1 performance targets
(section 8.1) and the four capability directions of 2026-10-21 (section 3),
whose initial-release-versus-future-release assignment requires explicit
confirmation.\
**Last updated:** 2026-10-21

## 1. Project Vision

Build a flexible, extensible e-commerce platform inspired by the
capabilities of nopCommerce, implemented independently with
Python/Django. The goal is to provide a maintainable foundation for an
online store that can be extended through plugins and themes.

This project is inspired by nopCommerce's functionality and extension
concepts; it is not a port or a copy of nopCommerce source code.

## 2. Technology Direction

-   **Backend:** Python and Django.
-   **API:** Django REST Framework (DRF), with an API-first approach.
-   **Frontend:** Standalone Vue.js application, built with Vite, consuming
    the backend API. Storefront themes are implemented with Vue layouts,
    components, and assets. Server-side rendering (SSR) is not introduced
    unless it is separately evaluated and approved.
-   **Administration interface:** Django Admin is the administration interface
    for the initial release. The administration interface is not part of the
    Vue/Vite storefront application and is not migrated to Vue in this phase.
    A future Vue-based custom administration interface is an optional,
    separately planned enhancement.
-   **UI framework:** Bootstrap for the storefront and custom UI. The initial
    Django Admin interface retains its built-in administration styling.
-   **Database:** SQL Server is the initial database. PostgreSQL is a
    potential future database target, not the currently selected database.
-   **ORM:** Django ORM is the preferred ORM because the backend uses Django
    and DRF. Database-specific logic must be isolated, and portable ORM
    features should be used where practical. SQLAlchemy is not introduced
    alongside Django ORM without explicit approval.
-   **Extensibility:** Plugin-based architecture and a theme system.

These are scope-level technology decisions. Detailed architecture and
implementation choices belong to a later phase. The compatible SQL Server
backend and minimum supported database version must be validated during
architecture/design.

## 3. Functional Scope

The platform is intended to cover the following capabilities:

-   Admin dashboard and access/permission management.
-   Customer accounts and authentication.
-   Product catalog: categories, brands, attributes, images, prices, and
    inventory.
-   Product variants and combinations of attributes.
-   Product search, filtering, sorting, and catalog browsing.
-   Shopping cart and checkout.
-   Orders, order status, and customer order history.
-   Multilingual storefront content and interface languages, including
    right-to-left (RTL) language support.
-   Payment methods and payment-related configuration.
-   Shipping methods and shipping-related configuration.
-   Discounts, coupons, and promotions.
-   Store settings, currency, and tax configuration.
-   Multi-currency pricing: a configurable base currency, customer selection
    of an active display/order currency, and explicitly configured prices for
    individual supported currencies. V1 uses only explicitly configured
    prices; automatic exchange-rate retrieval and automatic price conversion
    are deferred to a future release. If no explicit price is configured for
    the selected currency, the affected product or variant is not purchasable
    in that currency and the storefront must communicate that the price is
    unavailable without silently changing the customer's selected currency.
    Orders must preserve the currency and monetary amounts agreed when
    placed, and payment may be offered or initiated only with methods that
    support the order currency; the order currency is never changed to
    accommodate a payment provider.
-   Product reviews and ratings.
-   Notifications.
-   Reports and audit logs.
-   Plugin installation and management.
-   Theme installation, configuration, and activation.
-   Plugin-defined scheduled/background tasks: plugins can declare tasks
    that the platform's central application infrastructure schedules and
    executes, with manageable, observable execution and diagnosable
    outcomes.
-   An extensible application event and consumer mechanism: application
    components and plugins can publish application events and register
    consumers for event types they are interested in, so publishers and
    consumers remain loosely coupled. The concept is inspired by
    nopCommerce's event-consumer pattern; it is implemented
    project-specifically and is not a copy of its API.
-   Configurable CAPTCHA protection for applicable public forms, including
    support for Google reCAPTCHA, with administrative
    enable/disable/configuration and server-side token verification.
-   Customer registration extensibility compatible with future SMS-based
    verification: customer phone-number data and its verification status
    are representable where required, and SMS message delivery is possible
    through a provider-agnostic boundary. Actual SMS-based verification is
    a separate capability and is not approved for the initial release by
    this statement.

**Release assignment of the four capability directions above (2026-10-21)
is not decided.** Their inclusion in the initial release versus a future
release requires explicit user confirmation; corresponding requirements are
recorded in `REQUIREMENTS.md` (FR-PLUG-002, FR-EVT-001 – FR-EVT-004,
FR-CAPTCHA-001 – FR-CAPTCHA-006, FR-SMS-001 – FR-SMS-005) and open decisions
in its section 6.2 (UD-019 – UD-022). Nothing in these statements authorizes
implementation.

## 4. Product Variants and Attribute Combinations

Products may have attributes such as size, color, material, or other
configurable options. A product can have multiple combinations, and each
combination may have its own:

-   Price, including prices explicitly configured for supported currencies
    where applicable.
-   SKU or product code.
-   Stock quantity and availability.
-   Image or image set.
-   Validity or enabled/disabled state.

For example, size 4 + yellow may cost 500,000, size 4 + blue may cost
550,000, and size 5 + yellow may cost 600,000.

When a customer selects a combination, the storefront must show the
relevant price and availability. The selected combination must be
validated when adding the item to the cart and when placing the order.

## 5. UI and User Experience

-   The storefront UI uses Vue.js and Bootstrap. The initial administration
    interface uses Django Admin and is not required to use Vue in this
    release. A future Vue-based administration interface is optional and must
    be separately planned and approved.
-   The UI should be responsive and consistent across pages.
-   Reusable components should be used where appropriate.
-   Forms should provide validation feedback.
-   Loading, empty, success, and error states should be handled.
-   Accessibility and keyboard usability should be considered.
-   Themes and plugins should be able to extend supported UI areas
    without requiring arbitrary edits to core files.

## 6. Theme System and Theme-Aware Plugin UI

The platform must support installable themes. An administrator can
configure and activate a theme, and the active theme applies
consistently across supported storefront routes, including:

-   Homepage and product listing/detail pages.
-   Search and catalog pages.
-   Cart and checkout.
-   Authentication pages.
-   Customer profile, order history, order details, and wishlist.
-   Other storefront pages added by the platform or supported plugins.

The storefront remains a separate Vue/Vite application consuming the
Django REST Framework API. A theme is implemented with Vue layouts,
components, and assets; it is not implemented by making Django
server-side templates such as `.cshtml` or Django HTML templates control
the independent Vue storefront. Theme behavior is therefore defined in
terms of functional equivalents: a root layout, shared components, page
components, layout variants, and theme assets. SSR is out of scope unless
separately evaluated and approved.

### 6.1 Theme Settings

Themes may expose settings that administrators can configure through the
admin interface. The system should make it possible to install,
configure, activate, and deactivate themes.

### 6.2 Plugin UI Integration

Plugins may contribute UI components to relevant storefront regions
through approved Widget Zones and extension points. A plugin may provide
theme-aware components for specific supported themes, with a default
fallback component when a theme-specific implementation is unavailable.
Plugins must not need to overwrite arbitrary core or theme components to
contribute UI.

The exact folder layout, component-resolution mechanism, component
contracts, ordering rules, and fallback algorithm are architectural
decisions for a later phase; this scope does not prescribe their
implementation.

### 6.3 Navigation Extensions

Plugins may add menu items or submenus and may contribute links to
supported navigation areas, such as the main navigation or
customer-account navigation. The extension mechanism should support
appropriate ordering, visibility, and permission checks.

Plugins should not need to overwrite arbitrary core theme files to
extend navigation or page UI.

### 6.4 Theme Component Architecture

A theme must be able to control storefront presentation through Vue
components rather than server-rendered Django templates. Theme
customization includes:

-   A root layout component that defines the shared application shell and
    rendering regions.
-   Reusable shared components such as header, footer, navigation,
    metadata management, breadcrumbs, sidebars, product cards, galleries,
    pagination, cart components, account navigation, notifications, and
    messages.
-   Theme-specific page components for supported routes, including
    product, category/listing, cart, checkout, customer account, wishlist,
    order history, and other supported storefront pages.
-   A documented component-resolution contract that selects theme
    components when present and falls back to default components when a
    theme component is absent.
-   Layout variants such as full-width, one-column, two-column, and
    three-column layouts.
-   Theme-owned CSS, JavaScript, images, icons, fonts, and configuration.
-   Theme-aware plugin components supplied through approved Widget Zones.

The exact component names, route-to-page mapping, module format, build
integration, asset pipeline, and resolution algorithm are architectural
decisions for a later phase. Presentation components must consume
application data and services; they must not implement pricing, order,
inventory, permission, or other business rules.

## 7. UI Extension Points and Widget Zones

**Status: approved requirement.** Widget Zones and plugin UI extension
points are approved as requirements. The grouping below is an initial
coverage set, not the final exhaustive list of extension points. It is
inspired by widget-zone concepts in nopCommerce, but identifiers are
project-specific names and are not a promise of exact compatibility with
nopCommerce. The example names below describe conceptual placement; final
Vue Widget Zone identifiers are architecture/design decisions.

Plugins must be able to contribute Vue UI components to explicitly
defined Widget Zones. Depending on the zone's declared capabilities,
contributions may append content or replace a designated default
section. Replacement must only be allowed at zones explicitly designed
to support it; plugins must not arbitrarily replace core page content.
Each zone must support theme-compatible rendering, predictable ordering,
visibility and permission rules where relevant, and a defined fallback
when a plugin or theme-specific component is unavailable.

The extension-point registry must be extensible so that additional zones
can be introduced without rewriting core Vue components. The exact final
zone registry, identifiers, naming conventions, capabilities, and
ordering contract are architecture/design decisions.

### 7.1 Approved Coverage Groups

#### A. Global Layout

Examples:

-   `head_html_tag`
-   `body_start`
-   `content_before`
-   `content_after`
-   `header`
-   `header_before`
-   `header_after`
-   `footer`
-   `footer_before`
-   `footer_after`

#### B. Homepage

Examples:

-   `home_page_top`
-   `home_page_bottom`
-   `home_page_before_categories`
-   `home_page_before_products`
-   `home_page_before_news`

#### C. Category and Catalog Pages

Examples:

-   `category_details_top`
-   `category_details_after_breadcrumb`
-   `category_details_before_subcategories`
-   `category_details_before_filters`
-   `category_details_before_product_list`
-   `category_details_bottom`

#### D. Product Details

Examples:

-   `product_details_top`
-   `product_details_before_pictures`
-   `product_details_after_pictures`
-   `product_details_overview_top`
-   `product_details_overview_bottom`
-   `product_details_bottom`

#### E. Cart and Checkout

Initial coverage includes:

-   `shopping_cart_top`
-   `shopping_cart_bottom`
-   `checkout_top`
-   `checkout_bottom`
-   Extension points around order totals, shipping, payment, and
    checkout steps.

#### F. Customer Account

Extension points should be considered for:

-   Customer navigation.
-   Customer profile.
-   Order history and order details.
-   Wishlist.

#### G. Search, Manufacturers, and Other Catalog Pages

Extension points should be considered for search results, manufacturer
pages, and other catalog views.

#### H. Admin UI

Documented admin extension points should be supported where appropriate,
without compromising security or access control. In the initial release, the
administration interface and its extension points are Django Admin based;
storefront Vue theme components and Widget Zones do not control the admin
interface.

### 7.2 Detailed Definition Later

During detailed requirements and architecture, each extension point
must be documented with:

-   A stable identifier.
-   The Vue page or component for a storefront zone, or the Django Admin
    view/region for an admin zone, where it appears.
-   Its position in the page or component tree.
-   The contribution types allowed (for example, append or controlled
    replacement).
-   Theme-compatible rendering requirements.
-   Ordering and conflict-resolution rules.
-   Permission and visibility requirements, where relevant.
-   Compatibility and fallback behavior, including plugin default and
    theme-specific component fallback.

The extension-point list may be expanded as the platform's page flows
and plugin requirements are specified. The nopCommerce widget-zone
reference is useful as a source of ideas, not as a requirement to
reproduce every zone verbatim:

https://cdc1979.github.io/nopCommerce-Widget-Zones/

## 8. Non-Functional Requirements

-   **Security:** authentication, authorization, validation, and safe
    handling of sensitive operations.
-   **Extensibility:** plugins and themes should be able to add
    supported capabilities without unnecessary core modifications.
-   **Maintainability:** clear module boundaries and documented
    contracts.
-   **Testability:** automated tests for critical business rules and
    workflows.
-   **API quality:** documented and versionable APIs.
-   **Reliability:** consistent order, inventory, and payment state
    transitions.
-   **Performance:** responsive page and API behavior under expected
    workloads, as made measurable by the proposed V1 performance baseline in
    section 8.1.
-   **Accessibility:** usable interfaces across supported devices and
    interaction methods.
-   **Database portability:** database-specific queries and schema
    behavior must be isolated, and supported migrations must be evaluated
    against SQL Server. PostgreSQL may be evaluated as a future target,
    but switching databases must not be assumed to require only a
    configuration change.

Detailed measurable targets are defined in the proposed V1 performance
baseline below.

### 8.1 Proposed V1 Performance Baseline

The following performance targets are approved as proposed, provisional
baseline goals for the initial release. They are not a guarantee for every
deployment, no claim is made that they have been achieved, and they remain
subject to final review as part of this Draft. The detailed test conditions
and acceptance criteria are defined in `REQUIREMENTS.md`
(NFR-PERF-001 – NFR-PERF-003, AC-PERF-001 – AC-PERF-003).

**API response times** — measured under the baseline load test of 100
concurrent virtual users sustained for 30 minutes with a representative
workload mixture of storefront browsing, product detail retrieval, cart
operations, and checkout/order placement:

-   Read-only storefront API requests: p95 response time ≤ 300 ms target,
    with a maximum acceptance threshold of ≤ 500 ms.
-   Cart API requests: p95 target ≤ 500 ms, with a maximum acceptance
    threshold of ≤ 800 ms.
-   Order placement requests: p95 target ≤ 1,000 ms, with a maximum
    acceptance threshold of ≤ 2,000 ms, excluding external payment-provider
    processing and other explicitly documented external delays.

The p95 target is the design goal expected under the baseline load; the
maximum acceptance threshold is the upper bound at or below which the
acceptance criterion passes. Both values apply to the same measurement and
are complementary, not contradictory.

**Storefront user experience:**

-   Largest Contentful Paint (LCP) ≤ 2.5 seconds at the 75th percentile
    (p75) for a defined set of representative storefront pages, verified
    with a reproducible laboratory method. Real-user monitoring is not part
    of V1; this laboratory-only limitation is recorded with the test
    results.

**Baseline load test:**

-   100 concurrent virtual users for a sustained 30-minute run; measured
    error rate below 1%, excluding explicitly documented expected responses
    and test-harness errors.
-   The workload is a representative mixture of storefront browsing, product
    detail retrieval, cart operations, and checkout/order placement. The
    virtual-user count describes simulated client concurrency only; it does
    not imply 100 database connections, 100 orders per second, or any
    specific infrastructure sizing.

**Test conditions:** The environment, hardware, database configuration,
network conditions, test data volume, cache state, and exact workload
mixture must be recorded with every test result. Authentication, validation
failures, and intentionally slow external services must not be mixed into
normal successful-request measurements without an explicit explanation. The
final test environment and tooling details are established during
architecture and implementation planning (`REQUIREMENTS.md` section 6.2,
UD-018) and do not delay business-level approval of these requirements. No
specific server configuration is prescribed by this scope.

## 9. Out of Scope Unless Explicitly Approved

-   Native mobile applications.
-   A multi-vendor marketplace.
-   A microservices-first architecture.
-   Advanced AI-driven features.
-   Guaranteed compatibility with every existing nopCommerce plugin or
    theme.
-   Server-side rendering of the Vue storefront, unless separately
    evaluated and approved.
-   Introducing SQLAlchemy or another ORM alongside Django ORM without
    explicit approval.
-   Treating PostgreSQL as the current database or assuming migration
    from SQL Server requires only a configuration change.
-   Migrating the administration interface from Django Admin to Vue in the
    initial release. A future Vue-based admin is an optional, separately
    planned enhancement.
-   Refund processing and refund automation in the initial release; refunds
    are deferred to a future release by approved decision. Storing order and
    payment records does not constitute refund capability.
-   Automatic exchange-rate retrieval and automatic price conversion in v1;
    deferred to a future release by approved decision. V1 uses only
    explicitly configured currency prices.

## 10. Project Principles

1.  Follow a specification-first workflow.
2.  Use explicit phase gates: do not advance to the next phase without
    approval.
3.  Prefer an API-first design for the standalone Vue frontend.
4.  Use Bootstrap for the Vue storefront and custom UI; retain Django Admin's
    built-in administration styling in the initial release.
5.  Design for plugin and theme extensibility.
6.  Apply security by design.
7.  Add automated tests for critical behavior.
8.  Work incrementally and keep requirements traceable to design,
    implementation, and tests.

## 11. Approval Gate

The core project scope, including the product-variant and theme-system
requirements, has been approved in the discussion.

The Widget Zones and plugin UI extension points in section 7 are
approved as requirements. The exact zone registry, identifiers, and
naming conventions remain to be finalized during architecture/design.

This revision records the approved Vue/Vite theme, SQL Server with Django
ORM, Widget Zones, Django Admin, multi-currency pricing, and
multilingual/RTL support decisions, and the subsequently approved decisions
that refunds and automatic currency conversion are deferred to a future
release and that payment providers must support the order currency. It also
records the approved direction to adopt the proposed V1 performance baseline
in section 8.1 as provisional, testable goals for the initial release; it
does not claim those targets have been achieved and does not approve any
test infrastructure or implementation. The four capability directions added
on 2026-10-21 (section 3) are recorded as scope-level directions whose
release assignment still requires user confirmation. The revised scope and
requirements remain in Draft pending final user review and approval.

No architecture design, implementation task breakdown, or code
generation should begin until the user explicitly approves the relevant
scope and authorizes the next phase.
