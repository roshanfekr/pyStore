# MASTER INSTRUCTION — قوانین مشترک تمام فازها

این پروژه یک پلتفرم E-commerce حرفه‌ای و Production-ready مشابه nopCommerce است که با Python ساخته می‌شود.

معماری پایه پروژه:

* Python
* Django
* Django REST Framework
* PostgreSQL
* Redis
* Celery
* Pytest
* Modular Monolith
* Plugin-Based Architecture

اصول اصلی:

1. پروژه باید Modular Monolith باشد، نه Microservices.
2. Core نباید به Pluginهای خاص وابسته باشد.
3. قابلیت‌هایی که ممکن است در آینده تعویض یا توسعه داده شوند باید از طریق Interface، Service، Adapter، Event و Plugin قابل توسعه باشند.
4. Business Logic نباید داخل View یا API Controller قرار بگیرد.
5. ORM و Database Access باید در لایه مناسب معماری قرار بگیرد.
6. Configuration نباید Hard-code شود.
7. Secretها نباید داخل Repository ذخیره شوند.
8. تمام تغییرات باید با معماری فازهای قبلی سازگار باشند.
9. بدون دلیل موجه تکنولوژی یا ساختار قبلی را عوض نکن.
10. قبل از کدنویسی، Repository فعلی را بررسی کن.
11. فایل‌های موجود را بدون نیاز حذف یا بازنویسی کامل نکن.
12. قابلیت‌های فازهای آینده را زودتر پیاده‌سازی نکن.
13. برای هر Feature تست مناسب بنویس.
14. بعد از پیاده‌سازی تست‌ها را اجرا کن.
15. Errorهای ایجادشده توسط خودت را قبل از پایان فاز برطرف کن.
16. Migrationهای Database باید Versioned و Reversible باشند.
17. Type Hint و Validation مناسب استفاده کن.
18. Logging استاندارد داشته باش.
19. Dependencyها را حداقلی نگه دار.
20. Security را از ابتدا رعایت کن.

قاعده مهم:

قبل از شروع هر فاز:

* Repository را بررسی کن.
* ساختار فعلی را بررسی کن.
* فایل‌های مرتبط را بررسی کن.
* Migrationهای موجود را بررسی کن.
* تست‌های موجود را بررسی کن.
* وابستگی‌های فاز جدید را مشخص کن.

سپس Implementation را انجام بده.

در پایان هر فاز:

* تست‌ها را اجرا کن.
* خطاها را برطرف کن.
* Migrationها را بررسی کن.
* وضعیت پروژه را بررسی کن.
* فهرست فایل‌های ایجاد/تغییر یافته را گزارش کن.
* Featureهای تکمیل‌شده را گزارش کن.
* Featureهای ناقص را گزارش کن.
* مشکلات معماری احتمالی را گزارش کن.

هرگز فقط فایل تولید نکن؛ پروژه باید واقعاً قابل اجرا باشد.

---

# PHASE 00 — PROJECT FOUNDATION

هدف:

ایجاد اسکلت اولیه پروژه و استانداردهای توسعه.

پیاده‌سازی کن:

* Django project
* Environment configuration
* PostgreSQL connection
* Redis connection
* Celery infrastructure
* Logging
* Error handling پایه
* Health check
* Dockerfile
* docker-compose
* Development configuration
* Production configuration
* Pytest
* Test configuration
* GitIgnore
* Environment example
* README اولیه

ساختار اولیه پروژه را به شکل Modular طراحی کن.

حداقل بخش‌های پایه:

```text
src/
    config/
    core/
    apps/
    plugins/
tests/
scripts/
docker/
docs/
```

Core نباید شامل Business Domainهای فروشگاه باشد.

Health endpoint ایجاد کن.

Endpoint باید وضعیت حداقل موارد زیر را گزارش کند:

* Application
* Database
* Redis

Docker Compose باید بتواند محیط Development را بالا بیاورد.

Definition of Done:

* Application اجرا شود.
* PostgreSQL متصل شود.
* Redis متصل شود.
* Celery اجرا شود.
* Health check کار کند.
* Test suite اجرا شود.
* Docker environment اجرا شود.

در این فاز هیچ Feature فروشگاهی پیاده‌سازی نکن.

---

# PHASE 01 — CORE ARCHITECTURE

هدف:

ایجاد Core Framework داخلی برای پروژه.

پیاده‌سازی:

* Base Model
* Timestamp fields
* UUID/ID strategy
* Soft Delete strategy
* Base Service
* Repository abstraction
* Unit of Work در صورت نیاز
* Result/Error pattern در صورت نیاز
* Application services
* Domain events
* Event dispatcher
* Dependency injection strategy
* Exception hierarchy
* Common validators
* Common utilities

Business Domain را در Core قرار نده.

ساختار پیشنهادی:

```text
core/
    models/
    services/
    repositories/
    events/
    exceptions/
    permissions/
    validators/
    utils/
    infrastructure/
```

برای Event System امکان ارسال Eventهایی مانند زیر در آینده را فراهم کن:

```text
CustomerRegistered
ProductCreated
OrderCreated
PaymentCompleted
ShipmentCreated
```

Event System باید loosely coupled باشد.

تست کامل برای Core بنویس.

---

# PHASE 02 — PLUGIN ENGINE

این یکی از مهم‌ترین فازهای پروژه است.

یک Plugin System واقعی پیاده‌سازی کن.

هر Plugin باید بتواند:

* Discover شود
* Install شود
* Enable شود
* Disable شود
* Uninstall شود
* Upgrade شود
* Configuration داشته باشد
* Permission داشته باشد
* Service ثبت کند
* Route ثبت کند
* Event Handler ثبت کند
* Migration داشته باشد
* Admin UI داشته باشد
* Template داشته باشد
* Static file داشته باشد

ساختار پیشنهادی:

```text
plugins/
    sample_plugin/
        plugin.json
        plugin.py
        services.py
        routes.py
        events.py
        settings.py
        permissions.py
        migrations/
        templates/
        static/
        tests/
```

Plugin Manifest طراحی کن:

```text
id
name
version
author
description
dependencies
minimum_core_version
entry_point
```

Plugin Manager ایجاد کن با قابلیت:

```text
discover_plugins()
list_plugins()
get_plugin()
install_plugin()
uninstall_plugin()
enable_plugin()
disable_plugin()
upgrade_plugin()
```

Plugin Registry ایجاد کن.

Dependency Resolution پیاده‌سازی کن.

Plugin نباید برای نصب شدن نیازمند تغییر دستی Core باشد.

Plugin Settings باید از Settings عمومی سیستم جدا باشند.

یک Sample Plugin واقعی بساز.

برای تمام lifecycleها تست بنویس.

همچنین موارد زیر را تست کن:

* Invalid manifest
* Duplicate plugin
* Missing dependency
* Invalid version
* Disable plugin
* Uninstall dependency
* Failed installation
* Failed upgrade

---

# PHASE 03 — SETTINGS / EVENTS / CACHE / JOBS

سیستم‌های Cross-Cutting را تکمیل کن.

پیاده‌سازی:

### Settings

* Global settings
* Store settings
* Plugin settings
* Typed configuration
* Secure settings

### Events

* Event registration
* Event dispatch
* Sync handler
* Async handler

### Redis

* Cache abstraction
* Cache invalidation
* Namespaces

### Celery

* Task infrastructure
* Retry
* Failure handling
* Task logging
* Scheduled task support

سیستم‌ها باید طوری طراحی شوند که Pluginها بتوانند از آن‌ها استفاده کنند.

تست کامل بنویس.

---

# PHASE 04 — IDENTITY / USERS / ROLES / PERMISSIONS

سیستم Identity را پیاده‌سازی کن.

شامل:

* User
* Customer
* Staff/Admin user
* Roles
* Permissions
* Groups
* Authentication
* Password management
* Email verification
* Password reset
* Session management
* API authentication

RBAC واقعی پیاده‌سازی کن.

Permissionها باید granular باشند.

برای مثال:

```text
catalog.product.view
catalog.product.create
catalog.product.update
catalog.product.delete

order.view
order.edit
order.cancel
order.refund

customer.view
customer.edit
```

Permission system باید Plugin-aware باشد.

Pluginها بتوانند Permission جدید ثبت کنند.

---

# PHASE 05 — STORE / MULTI-STORE / VENDOR

سیستم Store را پیاده‌سازی کن.

پشتیبانی از:

* Store
* Store settings
* Store domain
* Store localization
* Store currency
* Store catalog settings

سیستم باید قابلیت Multi-store داشته باشد.

همچنین Vendor domain را طراحی و پیاده‌سازی کن.

Vendor باید بتواند:

* محصولات مربوط به خود را داشته باشد.
* سفارش‌های خود را ببیند.
* اطلاعات فروشنده داشته باشد.

Core نباید برای Vendor-specific logic به Plugin وابسته باشد.

تمام Relationshipها و Permissionها را پیاده‌سازی کن.

---

# PHASE 06 — CATALOG / PRODUCT

Catalog اصلی فروشگاه را پیاده‌سازی کن.

Entityهای اصلی:

* Product
* Product Variant
* Category
* Brand
* Tag
* Product Image
* Product Attribute
* Product Specification
* Product Relation
* Product Download
* Product SEO

Product باید امکان موارد زیر را داشته باشد:

* Simple Product
* Variant Product
* Digital Product
* Downloadable Product
* Recurring Product
* Bundled Product

برای Variant موارد زیر را پشتیبانی کن:

* SKU
* Price
* Compare-at price
* Weight
* Dimensions
* Stock
* Attributes

Category باید hierarchical باشد.

Product relation:

* Related products
* Cross-sell
* Upsell

توجه:

قیمت Product و Variant باید طوری طراحی شوند که سیستم Pricing آینده بتواند آن‌ها را override یا محاسبه کند.

---

# PHASE 07 — PRODUCT ATTRIBUTES / INVENTORY

سیستم Attribute و Inventory را تکمیل کن.

Attributes:

* Text
* Number
* Boolean
* Select
* Multi-select
* Color
* Size

Inventory:

* Stock quantity
* Reserved quantity
* Available quantity
* Stock status
* Backorder
* Low-stock threshold

Warehouse:

* Warehouse
* Warehouse inventory
* Warehouse location

Inventory transaction ایجاد کن.

تمام تغییرات موجودی باید قابل Audit باشند.

Overselling باید کنترل شود.

Concurrency مربوط به کاهش موجودی را به شکل صحیح مدیریت کن.

---

# PHASE 08 — PRICING / TAX / DISCOUNT

Pricing Engine را طراحی و پیاده‌سازی کن.

قابلیت‌ها:

* Base price
* Customer-specific price
* Role-specific price
* Store-specific price
* Quantity pricing
* Scheduled price
* Sale price

Discount Engine:

* Percentage discount
* Fixed amount
* Product discount
* Category discount
* Cart discount
* Customer discount
* Coupon
* Minimum order condition
* Maximum discount
* Start/end date
* Usage limits

Tax Engine:

* Tax classes
* Tax rates
* Country
* State/Province
* Customer tax settings
* Product tax settings

Pricing/Tax/Discount باید Plugin-friendly باشند.

---

# PHASE 09 — CART / WISHLIST / COMPARE

سیستم Shopping را پیاده‌سازی کن.

### Cart

* Guest cart
* Customer cart
* Add product
* Update quantity
* Remove product
* Product validation
* Inventory validation
* Price recalculation
* Discount application

### Wishlist

* Add
* Remove
* Move to cart

### Compare

* Add
* Remove
* Compare products

Cart باید persistent باشد.

Cart calculation را در Service مستقل قرار بده.

---

# PHASE 10 — CHECKOUT

Checkout Pipeline پیاده‌سازی کن.

مراحل:

```text
Cart
→ Customer
→ Address
→ Shipping
→ Tax
→ Discount
→ Payment
→ Order
```

از ابتدا مشخص کن که هر مرحله قابل extension توسط Plugin باشد.

Validationهای لازم:

* Product availability
* Inventory
* Price change
* Customer status
* Shipping availability
* Tax calculation
* Discount validity
* Payment availability

Checkout باید transactional باشد.

در صورت Failure نباید Order ناقص ایجاد شود.

---

# PHASE 11 — ORDER MANAGEMENT

Order Domain را پیاده‌سازی کن.

Entityها:

* Order
* OrderItem
* OrderAddress
* OrderNote
* OrderStatus
* PaymentStatus
* ShipmentStatus
* Refund
* Return

Order lifecycle دقیق طراحی کن.

حداقل:

```text
Pending
Processing
Paid
Shipped
Completed
Cancelled
Refunded
```

ولی Stateها را طوری طراحی کن که بعداً قابل extension باشند.

پشتیبانی از:

* Cancel order
* Partial cancellation
* Refund
* Partial refund
* Return
* Order notes
* Internal notes
* Customer notes
* Invoice information

تمام Transitionها باید Validation داشته باشند.

---

# PHASE 12 — PAYMENT / SHIPPING PLUGIN SYSTEM

Payment و Shipping را کاملاً Plugin-Based پیاده‌سازی کن.

Payment interface حداقل شامل مفاهیم:

```text
initialize_payment()
authorize()
capture()
void()
refund()
supports()
get_configuration()
```

Shipping interface:

```text
get_rates()
calculate_shipping()
create_shipment()
cancel_shipment()
get_tracking()
```

Plugin نمونه ایجاد کن:

```text
plugins/
    payment_dummy/
    shipping_dummy/
```

Dummy plugin باید واقعاً در Checkout قابل استفاده باشد.

Admin باید بتواند Pluginهای Payment/Shipping را Configuration کند.

---

# PHASE 13 — CMS / MEDIA / SEO

CMS را پیاده‌سازی کن.

شامل:

* Pages
* Blog
* Blog posts
* Categories
* Widgets
* Menus
* Blocks

Media System:

* Image
* Video
* File
* Media library
* Upload
* Delete
* Metadata
* Thumbnail

Media storage باید قابلیت تغییر به:

* Local filesystem
* S3-compatible storage

را داشته باشد.

SEO:

* Slug
* Meta title
* Meta description
* Canonical
* Robots
* Sitemap
* OpenGraph
* Structured data

---

# PHASE 14 — STOREFRONT / THEME SYSTEM

Frontend عمومی فروشگاه را پیاده‌سازی کن.

صفحات:

* Home
* Category
* Product
* Search
* Cart
* Checkout
* Login
* Register
* Customer account
* Wishlist
* Order details
* CMS pages
* Blog

Theme System ایجاد کن.

Theme باید قابلیت:

* Template override
* Static assets
* Configuration
* Widgets
* Layout
* Menu
* Branding

داشته باشد.

Theme architecture نباید Core را Modify کند.

---

# PHASE 15 — SEARCH

Search subsystem پیاده‌سازی کن.

در مرحله اول امکان استفاده از PostgreSQL search فراهم کن.

ساختار را طوری طراحی کن که بعداً Elasticsearch/OpenSearch به‌عنوان Plugin/Adapter اضافه شود.

امکانات:

* Full text search
* Product search
* Category search
* Filters
* Sorting
* Pagination
* Autocomplete
* Search suggestions
* Search indexing

Indexing باید بتواند توسط Background Job انجام شود.

---

# PHASE 16 — ADMIN PANEL

Admin Panel کامل ایجاد کن.

بخش‌ها:

```text
Dashboard
Catalog
Products
Categories
Brands
Inventory
Customers
Vendors
Orders
Payments
Shipments
Discounts
Coupons
Reviews
CMS
Media
Reports
Stores
Plugins
Users
Roles
Permissions
Settings
Logs
```

Admin باید Permission-aware باشد.

هر صفحه باید:

* List
* Search
* Filter
* Sort
* Pagination
* Create
* Edit
* Delete
* Bulk action

را در صورت نیاز داشته باشد.

برای عملیات حساس Confirmation اضافه کن.

---

# PHASE 17 — NOTIFICATION SYSTEM

Notification subsystem ایجاد کن.

کانال‌ها:

* Email
* In-app notification
* Webhook
* SMS abstraction

Notification template system ایجاد کن.

Template باید قابل Configuration باشد.

Eventهای نمونه:

```text
CustomerRegistered
OrderCreated
OrderPaid
OrderShipped
OrderCancelled
PasswordReset
```

Notificationها در صورت مناسب بودن Async باشند.

Notification providerها باید Plugin-Based باشند.

---

# PHASE 18 — API / WEBHOOK / INTEGRATION

API عمومی و Integration layer را کامل کن.

REST API برای:

* Authentication
* Customers
* Products
* Categories
* Cart
* Checkout
* Orders
* Payments
* Shipping

ایجاد کن.

API باید:

* Versioning
* Pagination
* Filtering
* Sorting
* Validation
* Error format
* Authentication
* Authorization
* Rate limiting

داشته باشد.

Webhook system ایجاد کن.

پشتیبانی از:

* Event
* Endpoint
* Secret
* Retry
* Signature
* Delivery log

را اضافه کن.

---

# PHASE 19 — REVIEWS / RATINGS / USER CONTENT

Review system را پیاده‌سازی کن.

شامل:

* Product review
* Rating
* Title
* Content
* Verified purchase
* Moderation
* Approval
* Rejection
* Admin review
* Customer review history

Spam/basic abuse protection اضافه کن.

Moderation باید در Admin قابل مدیریت باشد.

---

# PHASE 20 — SECURITY / AUDIT

Security hardening کامل پروژه را انجام بده.

بررسی و اصلاح:

* Authentication
* Authorization
* CSRF
* XSS
* SQL Injection
* SSRF
* Path traversal
* Unsafe file upload
* Session security
* Password policy
* Brute force
* Rate limiting
* Sensitive data exposure
* CORS
* Security headers
* Secret handling

Audit system:

* Actor
* Action
* Resource
* Resource ID
* Timestamp
* IP
* User agent
* Before/after data در موارد لازم

عملیات حساس باید Audit شوند.

---

# PHASE 21 — TESTING

Testing را به‌صورت جامع انجام بده.

Test layers:

```text
Unit
Integration
API
Database
Plugin
Security
End-to-End
```

حداقل برای Domainهای اصلی Coverage مناسب ایجاد کن.

تست‌های مهم:

* Product creation
* Inventory race condition
* Cart calculation
* Discount calculation
* Tax calculation
* Checkout
* Payment
* Order transition
* Plugin lifecycle
* Permis
