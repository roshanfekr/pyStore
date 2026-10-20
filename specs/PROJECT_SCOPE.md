# Project Scope --- Plugin-Based E-commerce Platform

**Document:** `specs/PROJECT_SCOPE.md`\
**Version:** 0.2 (draft with proposed widget-zone addition)\
**Status:** Core scope approved; the widget-zone grouping in section 7.4
is still awaiting explicit approval.\
**Last updated:** 2026-10-18

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
-   **Frontend:** Standalone Vue.js application consuming the backend
    API.
-   **UI framework:** Bootstrap.
-   **Database:** PostgreSQL.
-   **Extensibility:** Plugin-based architecture and a theme system.

These are scope-level technology decisions. Detailed architecture and
implementation choices belong to a later phase.

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
-   Payment methods and payment-related configuration.
-   Shipping methods and shipping-related configuration.
-   Discounts, coupons, and promotions.
-   Store settings, currency, and tax configuration.
-   Product reviews and ratings.
-   Notifications.
-   Reports and audit logs.
-   Plugin installation and management.
-   Theme installation, configuration, and activation.

## 4. Product Variants and Attribute Combinations

Products may have attributes such as size, color, material, or other
configurable options. A product can have multiple combinations, and each
combination may have its own:

-   Price.
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

-   The storefront and admin UI use Vue.js and Bootstrap.
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
consistently across storefront pages, including:

-   Homepage and product listing/detail pages.
-   Search and catalog pages.
-   Cart and checkout.
-   Authentication pages.
-   Customer profile, order history, order details, and wishlist.
-   Other storefront pages added by the platform or supported plugins.

### 6.1 Theme Settings

Themes may expose settings that administrators can configure through the
admin interface. The system should make it possible to install,
configure, activate, and deactivate themes.

### 6.2 Plugin UI Integration

Plugins may contribute UI to relevant pages through defined extension
points. A plugin may provide theme-aware views or components for
specific supported themes, with a default/fallback view when a
theme-specific implementation is unavailable.

The exact folder layout, rendering mechanism, component contracts, and
fallback algorithm are architectural decisions for a later phase; this
scope does not prescribe their implementation.

### 6.3 Navigation Extensions

Plugins may add menu items or submenus and may contribute links to
supported navigation areas, such as the main navigation or
customer-account navigation. The extension mechanism should support
appropriate ordering, visibility, and permission checks.

Plugins should not need to overwrite arbitrary core theme files to
extend navigation or page UI.

## 7. UI Extension Points and Widget Zones

**Status: proposed addition --- awaiting explicit approval.** The
grouping below is an initial coverage proposal, not the final exhaustive
list of extension points. It is inspired by widget-zone concepts in
nopCommerce, but identifiers are proposed names for this project and are
not a promise of exact compatibility with nopCommerce.

Plugins should be able to contribute UI to explicitly defined extension
points. Depending on the extension point's declared capabilities,
contributions may append content or replace a designated default
section. Replacement must only be allowed at points explicitly designed
to support it; plugins must not arbitrarily replace core page content.

### 7.1 Proposed Groups

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
without compromising security or access control.

### 7.2 Detailed Definition Later

During detailed requirements and architecture, each extension point
should be documented with:

-   A stable identifier.
-   The page or component where it appears.
-   Its position in the page.
-   The contribution types allowed (for example, append or controlled
    replacement).
-   Ordering and conflict-resolution rules.
-   Permission and visibility requirements, where relevant.
-   Compatibility and fallback behavior.

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
    workloads.
-   **Accessibility:** usable interfaces across supported devices and
    interaction methods.

Detailed measurable targets will be defined in later requirements work.

## 9. Out of Scope Unless Explicitly Approved

-   Native mobile applications.
-   A multi-vendor marketplace.
-   A microservices-first architecture.
-   Advanced AI-driven features.
-   Guaranteed compatibility with every existing nopCommerce plugin or
    theme.

## 10. Project Principles

1.  Follow a specification-first workflow.
2.  Use explicit phase gates: do not advance to the next phase without
    approval.
3.  Prefer an API-first design for the standalone Vue frontend.
4.  Use Bootstrap as the UI framework.
5.  Design for plugin and theme extensibility.
6.  Apply security by design.
7.  Add automated tests for critical behavior.
8.  Work incrementally and keep requirements traceable to design,
    implementation, and tests.

## 11. Approval Gate

The core project scope, including the product-variant and theme-system
requirements, has been approved in the discussion.

The widget-zone grouping in section 7.4 remains a proposal until
explicitly approved. Do not treat that proposed list as finalized.

No architecture design, implementation task breakdown, or code
generation should begin until the user explicitly approves the relevant
scope and authorizes the next phase.
