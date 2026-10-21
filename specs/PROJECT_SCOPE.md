# Project Scope --- Plugin-Based E-commerce Platform

**Document:** `specs/PROJECT_SCOPE.md`\
**Version:** 0.10 (recording the approved 2026-10-22 decisions on brand
listing and brand detail pages, the customer-managed address book, the
dedicated Contact Us page, and the Theme/Widget Zone implementation
sequence, on top of the previously recorded decisions, including the
2026-10-21 release assignment of the four capability directions and the
proposed V1 performance baseline)\
**Status:** Approved (2026-10-22). Version 0.10 was approved by the user on
2026-10-22 as the V1 scope baseline; no content was changed after that
approval. The core scope remains approved; this
revision records the user-approved decisions on the Vue/Vite theme system,
SQL Server with Django ORM, Widget Zones, the initial Django Admin interface,
multi-currency pricing, multilingual/RTL support, the deferral of refunds and
automatic currency conversion to a future release, and the rule that payment
providers must support the order currency. It additionally records the
approved direction to adopt proposed, provisional V1 performance targets
(section 8.1) and the approved 2026-10-21 release assignment of the four
capability directions (section 3): scheduled tasks, the event/consumer
mechanism, and Google reCAPTCHA are included in V1; SMS architectural
compatibility is required in V1 while actual SMS delivery and
phone-number verification are deferred to a later release. Revision 0.10
records the approved 2026-10-22 decisions (section 3 and section 6.5): brand
listing and brand detail pages with brand logo and SEO metadata, a
customer-managed address book with a default address and staff read-only
administrative access, a dedicated Contact Us page that stores the inquiry
and sends a notification, and the rule that preliminary Theme and Widget
Zone work may precede the content-page migration while completion of the
Theme and Widget Zone system follows the migration of the relevant content
pages to Vue.\
**Last updated:** 2026-10-22

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
-   Customer accounts and authentication, including a customer-managed address
    book: customers can create, view, update, and delete their own saved
    addresses, designate a default address, and select one of their own saved
    addresses at checkout. Staff can view customer addresses in the Django
    Admin but cannot edit them there. A selected address is copied into the
    order as an address snapshot, so later changes to or deletion of a saved
    address never alters an existing order. The reusable customer address
    entity is distinct from the order address snapshot.
-   Product catalog: categories, brands, attributes, images, prices, and
    inventory.
-   Brand listing and brand detail pages: the storefront lists active brands
    and provides a dedicated page for each active brand, showing the brand's
    published products with the relevant product browsing, filtering, and
    sorting capabilities. Brand information supports a name, a description, a
    logo, and SEO metadata. Inactive or unknown brands are not exposed
    through public brand listing or brand detail surfaces.
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
-   A dedicated Contact Us page with its own storefront route and page: the
    page presents the store's contact information and a contact form whose
    input is validated with clear feedback. A valid inquiry is stored and a
    notification is sent using the platform's existing notification
    capabilities. The contact page is a distinct route and page, not merely
    an informational page category, and is not satisfied by a generic CMS
    page. CAPTCHA behavior for the contact form remains subject to the open
    decision in `REQUIREMENTS.md` section 6.2 (UD-021).
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
    through a provider-agnostic boundary. Actual SMS message delivery and
    the phone-number verification workflow are deferred to a later release
    by approved decision; V1 preserves this architectural compatibility
    only.

**Approved release assignment (2026-10-21).** The user has approved the
initial-release assignment of these capability directions, limited to the
requirements already documented in `REQUIREMENTS.md` — no broader or
unspecified functionality is approved:

-   **Plugin-defined scheduled tasks — included in V1** (FR-PLUG-002):
    plugins register scheduled tasks with supported schedules or intervals,
    executed through shared platform infrastructure, with observable
    execution status and diagnosable failures.
-   **Application event and consumer mechanism — included in V1**
    (FR-EVT-001 – FR-EVT-004): independent consumers, supported entity
    lifecycle events, relevant business events, and the agreed
    synchronous/asynchronous delivery behavior. No delivery guarantee
    beyond the documented requirements (no exactly-once, guaranteed, or
    durable delivery) is approved.
-   **Google reCAPTCHA — included in V1** (FR-CAPTCHA-001 – FR-CAPTCHA-006):
    integration, administrative configuration, and server-side token
    verification as documented.
-   **SMS — architectural compatibility required in V1** (FR-SMS-001,
    FR-SMS-002): registration and identity flows must not preclude future
    SMS-based verification, with representable phone data/verification
    status and a provider-agnostic SMS delivery boundary. **Actual SMS
    message delivery and the phone-number verification workflow are
    deferred to a later release by approved decision** (FR-SMS-003,
    FR-SMS-004 apply only when that release is delivered); SMS delivery
    and verification are not V1 acceptance requirements.

Residual technical design questions (form policies, delivery guarantees,
task administration, future SMS policies) remain open in `REQUIREMENTS.md`
section 6.2 (UD-019 – UD-022). Nothing in these statements authorizes
implementation.

**Approved decisions (2026-10-22).** The user has approved the following
additions and sequencing constraint, limited to the requirements documented in
`REQUIREMENTS.md` — no broader or unspecified functionality is approved:

-   **Brand listing and brand detail pages — included in V1**: active brands
    are listed publicly, each active brand has a dedicated storefront page
    showing its published products with the relevant browsing, filtering, and
    sorting capabilities, brand information supports a name, a description, a
    logo, and SEO metadata, and inactive or unknown brands are not exposed
    through the public brand surfaces (FR-CAT-006, FR-CAT-007).
-   **Customer address book — included in V1**: customers manage their own
    saved addresses and may designate a default address; staff can view but
    not edit customer addresses in the Django Admin; checkout allows a
    customer to select one of their own addresses, and the selected address
    is copied into the order as an address snapshot that later changes to the
    saved address cannot alter (FR-CUST-002, FR-CHK-001).
-   **Dedicated Contact Us page — included in V1**: the contact form validates
    its input with clear feedback, a valid inquiry is stored, and a
    notification is sent using the existing notification capabilities; the
    page has its own route and is not satisfied by a generic CMS page
    (FR-CONTACT-001). CAPTCHA applicability stays open (UD-021).
-   **Theme and Widget Zone implementation sequence — approved constraint**:
    preliminary Theme and Widget Zone groundwork may be prepared before the
    content-page migration is complete, but completion of the full Theme and
    Widget Zone system follows the migration of the relevant content pages to
    Vue (section 6.5).

These decisions do not alter the previously approved V1 scope, including the
currency, refund, authentication, database, Django Admin, and Redis/Celery
decisions, and they do not close any open decision recorded in
`REQUIREMENTS.md` section 6.2.

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
-   Brand listing and brand detail pages.
-   Search and catalog pages.
-   Cart and checkout.
-   Authentication pages.
-   Customer profile, order history, order details, wishlist, and the
    customer address book.
-   Contact page.
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

### 6.5 Theme and Widget Zone Implementation Sequence (Approved 2026-10-22)

The order in which the Theme system and the Widget Zone system are completed
is an approved implementation constraint, not a prohibition on early
groundwork.

-   Preliminary Theme and Widget Zone work — such as defining the zone
    registry contract, the component-resolution rules, the theme package
    format, and the migration of individual routes — may be prepared before
    the content-page migration is complete.
-   Completion of the full Theme and Widget Zone system follows the migration
    of the relevant content pages to the Vue storefront. A theme or Widget
    Zone capability is complete only when the corresponding storefront
    content is served by the Vue storefront and the zone is actually rendered
    there.
-   Until a route or zone has been migrated, the existing server-rendered
    mechanism remains in place as a documented interim state and is retired
    when that route or zone is migrated. The route-by-route migration state
    and the actual Widget Zone rendering state are tracked in
    `STORE_FRONT_ROUTE_COVERAGE.md`.
-   The sequence does not change any business behavior, API behavior, or
    data, and it does not change the requirement that the Vue storefront
    ultimately owns the supported routes.

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
-   Customer address book.

#### G. Search, Manufacturers, and Other Catalog Pages

Extension points should be considered for search results, manufacturer
pages, and other catalog views.

Brand listing and brand detail pages are part of the category and catalog
coverage group and receive the corresponding listing-page extension points.

#### H. Admin UI

Documented admin extension points should be supported where appropriate,
without compromising security or access control. In the initial release, the
administration interface and its extension points are Django Admin based;
storefront Vue theme components and Widget Zones do not control the admin
interface.

#### I. Contact and Other Customer-Facing Pages

Extension points should be considered for the contact page, including the
form area and the surrounding informational regions. The final zone
identifier, capability, and placement remain architecture/design decisions
(`REQUIREMENTS.md` section 6.2, UD-007).

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
-   Actual SMS message delivery and the SMS-based registration /
    phone-number verification workflow in v1; deferred to a later release
    by approved decision. V1 preserves architectural compatibility only
    (section 3).

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
on 2026-10-21 (section 3) have received an approved release assignment:
scheduled tasks, the event/consumer mechanism, and Google reCAPTCHA are
included in V1, and SMS architectural compatibility is required in V1 while
SMS delivery and phone-number verification are deferred to a later release.
The revised scope and requirements were approved by the user on 2026-10-22
(`REQUIREMENTS.md` v0.12, `ARCHITECTURE.md` v0.9). Approval of the scope does
not by itself authorize implementation: architecture design, implementation
task breakdown, or code generation still begin only when the user
authorizes the next phase. The phased plan derived from the approved scope,
requirements, and architecture is recorded in `IMPLEMENTATION_PLAN.md`.
