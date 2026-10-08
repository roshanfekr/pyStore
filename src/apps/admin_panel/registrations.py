from django.contrib import admin, messages
from django import forms
from django.template.response import TemplateResponse
from django.utils.text import slugify

from apps.admin_panel.widgets import TagPickerWidget
from apps.cart.models import Cart, CartItem, CompareItem, WishlistItem
from apps.catalog.models import (
    Brand,
    Category,
    Product,
    ProductAttribute,
    ProductAttributeValue,
    ProductBundleItem,
    ProductDownload,
    ProductImage,
    ProductRelation,
    ProductSEO,
    ProductSpecification,
    ProductVariant,
    Tag,
)
from apps.checkout.models import PaymentMethod, ShippingMethod
from apps.cms.models import BlogCategory, BlogPost, ContentBlock, Menu, MenuItem, Page, Widget
from apps.identity.models import Customer, Permission, Role, User
from apps.inventory.models import InventoryItem, InventoryTransaction, Warehouse, WarehouseLocation
from apps.notifications.models import (
    Notification,
    NotificationMessage,
    NotificationTemplate,
    WebhookEndpoint,
)
from apps.orders.models import (
    Order,
    OrderAddress,
    OrderItem,
    OrderNote,
    OrderStatusLog,
    Refund,
    ReturnRequest,
    ReturnRequestItem,
)
from apps.orders.services import (
    approve_return,
    cancel_order,
    reject_return,
    set_shipment_status,
    transition_order_status,
)
from apps.pricing.models import (
    CustomerTaxInfo,
    Discount,
    DiscountUsage,
    PriceList,
    PriceListEntry,
    ProductTaxSetting,
    ScheduledPrice,
    TaxClass,
    TaxRate,
)
from apps.reviews.models import ProductReview
from apps.stores.models import Language, LocaleStringResource, Store, StoreDomain
from apps.vendors.models import Vendor, VendorUser
from core.audit.models import AuditLog
from core.exceptions import ValidationError
from core.plugins.models import PluginState

CANCELLABLE_STATUSES = (Order.STATUS_PENDING, Order.STATUS_PROCESSING, Order.STATUS_PAID)


class DeletedListFilter(admin.SimpleListFilter):
    title = "deleted state"
    parameter_name = "deleted"

    def lookups(self, request, model_admin):
        return (("no", "Active only"), ("yes", "Deleted"))

    def queryset(self, request, queryset):
        model = queryset.model
        if self.value() == "yes":
            if hasattr(model, "all_objects"):
                return model.all_objects.filter(is_deleted=True)
            return queryset.none()
        if self.value() == "no":
            if hasattr(model, "is_deleted"):
                return queryset.filter(is_deleted=False)
            return queryset
        return queryset


class PyStoreModelAdmin(admin.ModelAdmin):
    """Base admin for soft-delete models.

    Hides the is_deleted bookkeeping fields from forms (deleting is done
    with the standard Delete button — the model's delete() is a soft delete)
    and adds a deleted-state filter plus a restore bulk action.
    """

    exclude = ("is_deleted", "deleted_at")

    def get_list_filter(self, request):
        return tuple(super().get_list_filter(request)) + (DeletedListFilter,)

    def get_actions(self, request):
        actions = dict(super().get_actions(request))
        actions.setdefault(
            "restore_selected",
            (
                PyStoreModelAdmin.restore_selected,
                "restore_selected",
                "Restore selected (undo delete)",
            ),
        )
        return actions

    @admin.action(description="Restore selected (undo delete)")
    def restore_selected(self, request, queryset):
        restored = 0
        for obj in queryset:
            if getattr(obj, "is_deleted", False):
                obj.restore()
                restored += 1
        self.message_user(request, f"{restored} item(s) restored.")


class ReadOnlyAdmin(PyStoreModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class GranularPermissionAdmin(PyStoreModelAdmin):
    """Gates write actions on granular dotted permissions.

    perm_map keys: add / change / delete. Superusers pass through the
    identity PermissionBackend (they hold every seeded codename).
    """

    perm_map: dict[str, str] = {}

    def _perm(self, request, action: str) -> bool:
        codename = self.perm_map.get(action)
        return bool(codename) and request.user.has_perm(codename)

    def has_add_permission(self, request):
        return self._perm(request, "add")

    def has_change_permission(self, request, obj=None):
        return self._perm(request, "change")

    def has_delete_permission(self, request, obj=None):
        return self._perm(request, "delete")


def confirm_action(request, model_admin, queryset, action_name, title, warning):
    context = dict(
        model_admin.admin_site.each_context(request),
        queryset=queryset,
        action_name=action_name,
        title=title,
        warning=warning,
        opts=model_admin.model._meta,
    )
    return TemplateResponse(request, "admin_panel/confirm_action.html", context)


class CategoryAdmin(PyStoreModelAdmin):
    list_display = ("name", "slug", "parent", "is_active", "ordering")
    list_filter = ("is_active", "parent")
    search_fields = ("name", "slug")


class BrandAdmin(PyStoreModelAdmin):
    list_display = ("name", "slug", "is_active")
    search_fields = ("name",)
    list_filter = ("is_active",)


class TagAdmin(PyStoreModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name",)


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 0


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 0


class ProductSpecificationInline(admin.TabularInline):
    model = ProductSpecification
    extra = 0


class ProductSEOInline(admin.StackedInline):
    model = ProductSEO
    extra = 0


class ProductAdminForm(forms.ModelForm):
    """Product form with a free-text tag picker instead of a select list."""

    tags_input = forms.CharField(
        required=False,
        label="Tags",
        widget=TagPickerWidget,
        help_text="Type a tag and press Enter. New tags are created automatically.",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields.pop("tags", None)
        if self.instance and self.instance.pk:
            self.initial["tags_input"] = ", ".join(
                self.instance.tags.values_list("name", flat=True)
            )

    def clean_tags_input(self):
        raw = self.cleaned_data.get("tags_input") or ""
        seen, names = set(), []
        for part in raw.split(","):
            name = part.strip()
            if not name:
                continue
            key = name.casefold()
            if key not in seen:
                seen.add(key)
                names.append(name)
        return names

    class Meta:
        model = Product
        fields = "__all__"


class ProductAdmin(PyStoreModelAdmin):
    list_display = ("name", "slug", "store", "product_type", "price", "stock_quantity", "is_published")
    list_filter = ("product_type", "is_published", "store", "brand")
    search_fields = ("name", "slug", "sku", "description")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    form = ProductAdminForm
    inlines = [ProductVariantInline, ProductImageInline, ProductSpecificationInline, ProductSEOInline]
    actions = ["publish_products", "unpublish_products"]

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        return [
            (
                title,
                {
                    **options,
                    "fields": [
                        field
                        for field in options.get("fields", ())
                        if field != "tags"
                    ],
                },
            )
            for title, options in fieldsets
        ]

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        names = form.cleaned_data.get("tags_input") or []
        tags = []
        for name in names:
            slug = slugify(name, allow_unicode=True) or slugify(name) or f"tag-{abs(hash(name)) % 10**8}"
            tag = Tag.objects.filter(name__iexact=name).first() or Tag.objects.filter(slug=slug).first()
            if tag is None:
                tag = Tag.objects.create(name=name, slug=slug)
            tags.append(tag)
        form.instance.tags.set(tags)

    @admin.action(description="Publish selected products")
    def publish_products(self, request, queryset):
        updated = queryset.update(is_published=True)
        self.message_user(request, f"{updated} product(s) published.")

    @admin.action(description="Unpublish selected products")
    def unpublish_products(self, request, queryset):
        updated = queryset.update(is_published=False)
        self.message_user(request, f"{updated} product(s) unpublished.")


class ProductAttributeAdmin(PyStoreModelAdmin):
    list_display = ("name", "slug", "value_type", "is_variant_option")
    list_filter = ("value_type",)
    search_fields = ("name", "slug")


class ProductAttributeValueAdmin(PyStoreModelAdmin):
    list_display = ("attribute", "value", "position")
    list_filter = ("attribute",)


class WarehouseAdmin(PyStoreModelAdmin):
    list_display = ("name", "code", "store", "city", "is_default")
    search_fields = ("name", "code")


class WarehouseLocationAdmin(PyStoreModelAdmin):
    list_display = ("warehouse", "code")
    search_fields = ("code",)


class InventoryItemAdmin(PyStoreModelAdmin):
    list_display = (
        "__str__", "warehouse", "stock_quantity", "reserved_quantity",
        "low_stock_threshold", "stock_status",
    )
    list_filter = ("warehouse", "backorder_allowed")
    search_fields = ("product__name", "variant__sku")


class InventoryTransactionAdmin(ReadOnlyAdmin):
    list_display = (
        "inventory_item", "transaction_type", "stock_delta", "reserved_delta",
        "resulting_stock", "actor", "created_at",
    )
    list_filter = ("transaction_type",)
    date_hierarchy = "created_at"


class UserAdmin(GranularPermissionAdmin):
    perm_map = {"add": "identity.users.manage", "change": "identity.users.manage", "delete": "identity.users.manage"}
    list_display = ("email", "user_type", "is_active", "is_staff", "email_verified", "date_joined")
    list_filter = ("user_type", "is_active", "is_staff", "email_verified")
    search_fields = ("email", "first_name", "last_name")
    ordering = ("-date_joined",)
    fields = (
        "email", "first_name", "last_name", "user_type", "email_verified",
        "is_active", "is_staff", "is_superuser",
    )

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if "password" in form.base_fields:
            del form.base_fields["password"]
        return form


class CustomerAdmin(PyStoreModelAdmin):
    list_display = ("id", "user", "phone")
    search_fields = ("user__email", "phone")


class RoleAdmin(GranularPermissionAdmin):
    perm_map = {"add": "identity.roles.manage", "change": "identity.roles.manage", "delete": "identity.roles.manage"}
    list_display = ("name", "is_system", "display_permissions")
    search_fields = ("name",)
    filter_horizontal = ("permissions", "users")

    @admin.display(description="Permissions")
    def display_permissions(self, obj):
        return ", ".join(p.codename for p in obj.permissions.all()[:5])


class PermissionAdmin(GranularPermissionAdmin):
    perm_map = {"add": "identity.roles.manage", "change": "identity.roles.manage", "delete": "identity.roles.manage"}
    list_display = ("codename", "source", "display_name")
    list_filter = ("source",)
    search_fields = ("codename",)


class OrderAdmin(PyStoreModelAdmin):
    list_display = (
        "number", "store", "email", "status", "payment_status", "shipment_status", "total", "created_at",
    )
    list_filter = ("status", "payment_status", "shipment_status", "store")
    search_fields = ("number", "email")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    actions = ["cancel_orders", "mark_shipped", "mark_paid"]

    @admin.action(description="Cancel selected orders (confirmation required)")
    def cancel_orders(self, request, queryset):
        if not request.user.has_perm("order.cancel"):
            messages.error(request, "Permission denied: 'order.cancel' permission required.")
            return None

        if request.POST.get("confirm") != "yes":
            return confirm_action(
                request, self, queryset, "cancel_orders",
                "Cancel selected orders?",
                "This will cancel the orders and restock reserved inventory. This action cannot be undone.",
            )

        cancelled, skipped = 0, 0
        for order in queryset:
            if order.status in CANCELLABLE_STATUSES:
                cancel_order(order, actor=request.user, note="Cancelled from admin panel")
                cancelled += 1
            else:
                skipped += 1
        self.message_user(
            request,
            f"{cancelled} order(s) cancelled." + (f" {skipped} skipped (status not cancellable)." if skipped else ""),
        )
        return None

    @admin.action(description="Mark selected orders as paid")
    def mark_paid(self, request, queryset):
        if not request.user.has_perm("order.edit"):
            messages.error(request, "Permission denied: 'order.edit' permission required.")
            return None
        for order in queryset:
            if order.payment_status == Order.PAYMENT_PENDING:
                from apps.orders.services import set_payment_status

                set_payment_status(order, Order.PAYMENT_PAID, actor=request.user)
        self.message_user(request, "Selected orders marked as paid.")

    @admin.action(description="Mark selected orders as shipped (confirmation required)")
    def mark_shipped(self, request, queryset):
        if not request.user.has_perm("order.edit"):
            messages.error(request, "Permission denied: 'order.edit' permission required.")
            return None

        if request.POST.get("confirm") != "yes":
            return confirm_action(
                request, self, queryset, "mark_shipped",
                "Mark selected orders as shipped?",
                "Only orders with 'paid' status can transition to shipped.",
            )

        shipped, skipped = 0, 0
        for order in queryset:
            try:
                transition_order_status(order, Order.STATUS_SHIPPED, actor=request.user)
                set_shipment_status(order, Order.SHIPMENT_SHIPPED, actor=request.user)
                shipped += 1
            except ValidationError:
                skipped += 1
        self.message_user(request, f"{shipped} order(s) shipped." + (f" {skipped} skipped." if skipped else ""))
        return None


class OrderItemAdmin(PyStoreModelAdmin):
    list_display = ("order", "product_name", "sku", "quantity", "unit_price", "line_total")
    search_fields = ("product_name", "sku", "order__number")


class OrderStatusLogAdmin(ReadOnlyAdmin):
    list_display = ("order", "status_type", "from_value", "to_value", "actor", "created_at")
    list_filter = ("status_type",)
    date_hierarchy = "created_at"


class RefundAdmin(ReadOnlyAdmin):
    list_display = ("order", "amount", "reason", "actor", "created_at")
    date_hierarchy = "created_at"


class ReturnRequestAdmin(PyStoreModelAdmin):
    list_display = ("order", "status", "reason", "user", "created_at")
    list_filter = ("status",)
    actions = ["approve_requests", "reject_requests"]

    @admin.action(description="Approve selected return requests")
    def approve_requests(self, request, queryset):
        for return_request in queryset.filter(status=ReturnRequest.STATUS_REQUESTED):
            approve_return(return_request, actor=request.user)
        self.message_user(request, "Requested returns approved.")

    @admin.action(description="Reject selected return requests")
    def reject_requests(self, request, queryset):
        for return_request in queryset.filter(status=ReturnRequest.STATUS_REQUESTED):
            reject_return(return_request, actor=request.user)
        self.message_user(request, "Requested returns rejected.")


class PriceListAdmin(GranularPermissionAdmin):
    perm_map = {"add": "pricing.manage", "change": "pricing.manage", "delete": "pricing.manage"}
    list_display = ("name", "store", "role", "customer", "priority", "is_active")
    list_filter = ("is_active",)
    inlines = []


class PriceListEntryAdmin(PyStoreModelAdmin):
    list_display = ("price_list", "product", "variant", "price", "min_quantity", "max_quantity")


class ScheduledPriceAdmin(PyStoreModelAdmin):
    list_display = ("product", "variant", "price", "start_at", "end_at", "is_active")
    list_filter = ("is_active",)


class DiscountAdmin(GranularPermissionAdmin):
    perm_map = {"add": "discounts.manage", "change": "discounts.manage", "delete": "discounts.manage"}
    list_display = ("name", "coupon_code", "discount_type", "value", "scope", "used_count", "is_active")
    list_filter = ("discount_type", "scope", "is_active")
    search_fields = ("name", "coupon_code")
    actions = ["activate_discounts", "deactivate_discounts"]

    @admin.action(description="Activate selected discounts")
    def activate_discounts(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} discount(s) activated.")

    @admin.action(description="Deactivate selected discounts")
    def deactivate_discounts(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} discount(s) deactivated.")


class DiscountUsageAdmin(ReadOnlyAdmin):
    list_display = ("discount", "user", "reference", "used_at")


class TaxClassAdmin(GranularPermissionAdmin):
    perm_map = {"add": "taxes.manage", "change": "taxes.manage", "delete": "taxes.manage"}
    list_display = ("name", "is_default")


class TaxRateAdmin(GranularPermissionAdmin):
    perm_map = {"add": "taxes.manage", "change": "taxes.manage", "delete": "taxes.manage"}
    list_display = ("name", "tax_class", "rate", "country", "state", "is_active")
    list_filter = ("tax_class", "is_active")


class LanguageAdmin(GranularPermissionAdmin):
    perm_map = {"add": "stores.manage", "change": "stores.manage", "delete": "stores.manage"}
    list_display = ("name", "code", "direction", "is_active", "is_default", "ordering")
    list_editable = ("is_active", "ordering")
    list_filter = ("is_active", "direction", "is_default")
    search_fields = ("name", "code")
    fields = ("name", "code", "is_active", "is_default", "direction", "flag", "ordering")


class LocaleStringResourceAdmin(GranularPermissionAdmin):
    perm_map = {"add": "stores.manage", "change": "stores.manage", "delete": "stores.manage"}
    list_display = ("key", "language", "value_snippet")
    list_filter = ("language",)
    search_fields = ("key", "value")
    list_select_related = ("language",)

    @admin.display(description="Value")
    def value_snippet(self, obj):
        return obj.value[:80]

    def get_queryset(self, request):
        return super().get_queryset(request).filter(language__is_active=True)


class StoreAdmin(GranularPermissionAdmin):
    perm_map = {"add": "stores.manage", "change": "stores.manage", "delete": "stores.manage"}
    list_display = ("name", "slug", "is_default", "is_active", "default_currency")
    search_fields = ("name", "slug")


class StoreDomainAdmin(GranularPermissionAdmin):
    perm_map = {"add": "stores.manage", "change": "stores.manage", "delete": "stores.manage"}
    list_display = ("domain", "store", "is_primary", "ssl_enabled")
    search_fields = ("domain",)


class VendorAdmin(GranularPermissionAdmin):
    perm_map = {"add": "vendor.manage", "change": "vendor.manage", "delete": "vendor.manage"}
    list_display = ("name", "slug", "status", "store", "owner")
    list_filter = ("status",)
    search_fields = ("name", "slug")


class VendorUserAdmin(PyStoreModelAdmin):
    list_display = ("vendor", "user", "is_admin")


class PaymentMethodAdmin(PyStoreModelAdmin):
    list_display = ("name", "code", "is_active")
    list_filter = ("is_active",)


class ShippingMethodAdmin(PyStoreModelAdmin):
    list_display = ("name", "code", "store", "flat_price", "is_active")
    list_filter = ("store", "is_active")


class PageAdmin(PyStoreModelAdmin):
    list_display = ("title", "slug", "is_published")
    search_fields = ("title", "slug")
    list_filter = ("is_published",)


class BlogPostAdmin(PyStoreModelAdmin):
    list_display = ("title", "slug", "author", "is_published", "published_at")
    search_fields = ("title",)
    list_filter = ("is_published",)


class MenuAdmin(PyStoreModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name",)


class WidgetAdmin(PyStoreModelAdmin):
    list_display = ("name", "slug", "widget_type", "is_active")
    list_filter = ("widget_type", "is_active")


class ContentBlockAdmin(PyStoreModelAdmin):
    list_display = ("name", "slug", "is_active")
    search_fields = ("name", "slug")


class MediaFileAdmin(PyStoreModelAdmin):
    list_display = ("original_name", "media_type", "size", "uploaded_by", "created_at")
    list_filter = ("media_type",)
    search_fields = ("original_name",)

    def has_add_permission(self, request):
        return False


class NotificationTemplateAdmin(PyStoreModelAdmin):
    list_display = ("code", "event_name", "channel", "store", "is_active")
    list_filter = ("channel", "is_active", "store")
    search_fields = ("code", "name", "event_name")


class WebhookEndpointAdmin(PyStoreModelAdmin):
    list_display = ("target_url", "is_active", "display_events", "description")
    list_filter = ("is_active",)
    search_fields = ("target_url",)

    @admin.display(description="Events")
    def display_events(self, obj):
        return ", ".join(obj.event_names or []) or "*"


class NotificationMessageAdmin(ReadOnlyAdmin):
    list_display = (
        "event_name", "channel", "provider_code", "recipient", "status",
        "attempts", "created_at",
    )
    list_filter = ("channel", "status")
    search_fields = ("recipient", "event_name")
    date_hierarchy = "created_at"


class NotificationAdmin(PyStoreModelAdmin):
    list_display = ("user", "title", "level", "is_read", "read_at", "created_at")
    list_filter = ("level", "is_read")
    search_fields = ("title", "user__email")
    actions = ["mark_as_read"]

    @admin.action(description="Mark selected notifications as read")
    def mark_as_read(self, request, queryset):
        from apps.notifications.services import mark_notification_read

        count = 0
        for notification in queryset.filter(is_read=False):
            mark_notification_read(notification)
            count += 1
        self.message_user(request, f"{count} notification(s) marked as read.")


class ProductReviewAdmin(PyStoreModelAdmin):
    list_display = (
        "product", "user", "rating", "status", "is_verified_purchase",
        "moderated_by", "created_at",
    )
    list_filter = ("status", "rating", "is_verified_purchase")
    search_fields = ("product__name", "user__email", "title", "content")
    readonly_fields = ("is_verified_purchase", "ip_address")
    actions = ["approve_reviews", "reject_reviews"]

    @admin.action(description="Approve selected reviews (confirmation required)")
    def approve_reviews(self, request, queryset):
        from apps.reviews.permissions import REVIEWS_PERMISSIONS

        if not request.user.has_perm(REVIEWS_PERMISSIONS[0][0]):
            messages.error(request, "Permission denied: 'reviews.review.moderate' required.")
            return None
        if request.POST.get("confirm") != "yes":
            return confirm_action(
                request, self, queryset, "approve_reviews",
                "Approve selected reviews?",
                "Approved reviews become publicly visible on the storefront.",
            )
        approved = 0
        for review in queryset.filter(status=ProductReview.STATUS_PENDING):
            from apps.reviews.services import approve_review

            approve_review(review, actor=request.user)
            approved += 1
        self.message_user(request, f"{approved} review(s) approved.")
        return None

    @admin.action(description="Reject selected reviews (confirmation required)")
    def reject_reviews(self, request, queryset):
        from apps.reviews.permissions import REVIEWS_PERMISSIONS

        if not request.user.has_perm(REVIEWS_PERMISSIONS[0][0]):
            messages.error(request, "Permission denied: 'reviews.review.moderate' required.")
            return None
        if request.POST.get("confirm") != "yes":
            return confirm_action(
                request, self, queryset, "reject_reviews",
                "Reject selected reviews?",
                "Rejected reviews are hidden from the storefront.",
            )
        rejected = 0
        for review in queryset.filter(status=ProductReview.STATUS_PENDING):
            from apps.reviews.services import reject_review

            reject_review(review, actor=request.user, reason="Rejected from admin panel")
            rejected += 1
        self.message_user(request, f"{rejected} review(s) rejected.")
        return None


class AuditLogAdmin(ReadOnlyAdmin):
    list_display = (
        "action", "resource", "resource_id", "actor_email", "ip_address", "created_at",
    )
    list_filter = ("action", "resource")
    search_fields = ("resource_id", "actor_email", "action")
    date_hierarchy = "created_at"


class PluginStateAdmin(PyStoreModelAdmin):
    list_display = ("plugin_id", "name", "version", "status", "installed_at", "updated_at")
    list_filter = ("status",)
    search_fields = ("plugin_id", "name")


def register_all(admin_site):
    registrations = {
        Category: CategoryAdmin,
        Brand: BrandAdmin,
        Tag: TagAdmin,
        Product: ProductAdmin,
        ProductAttribute: ProductAttributeAdmin,
        ProductAttributeValue: ProductAttributeValueAdmin,
        ProductBundleItem: PyStoreModelAdmin,
        ProductDownload: PyStoreModelAdmin,
        ProductRelation: PyStoreModelAdmin,
        Warehouse: WarehouseAdmin,
        WarehouseLocation: WarehouseLocationAdmin,
        InventoryItem: InventoryItemAdmin,
        InventoryTransaction: InventoryTransactionAdmin,
        User: UserAdmin,
        Customer: CustomerAdmin,
        Role: RoleAdmin,
        Permission: PermissionAdmin,
        Order: OrderAdmin,
        OrderItem: OrderItemAdmin,
        OrderStatusLog: OrderStatusLogAdmin,
        Refund: RefundAdmin,
        ReturnRequest: ReturnRequestAdmin,
        ReturnRequestItem: PyStoreModelAdmin,
        OrderNote: PyStoreModelAdmin,
        OrderAddress: PyStoreModelAdmin,
        PriceList: PriceListAdmin,
        PriceListEntry: PriceListEntryAdmin,
        ScheduledPrice: ScheduledPriceAdmin,
        Discount: DiscountAdmin,
        DiscountUsage: DiscountUsageAdmin,
        TaxClass: TaxClassAdmin,
        TaxRate: TaxRateAdmin,
        CustomerTaxInfo: PyStoreModelAdmin,
        ProductTaxSetting: PyStoreModelAdmin,
        Store: StoreAdmin,
        StoreDomain: StoreDomainAdmin,
        Language: LanguageAdmin,
        LocaleStringResource: LocaleStringResourceAdmin,
        Vendor: VendorAdmin,
        VendorUser: VendorUserAdmin,
        PaymentMethod: PaymentMethodAdmin,
        ShippingMethod: ShippingMethodAdmin,
        Page: PageAdmin,
        BlogCategory: PyStoreModelAdmin,
        BlogPost: BlogPostAdmin,
        Menu: MenuAdmin,
        MenuItem: PyStoreModelAdmin,
        Widget: WidgetAdmin,
        ContentBlock: ContentBlockAdmin,
        Cart: PyStoreModelAdmin,
        CartItem: PyStoreModelAdmin,
        WishlistItem: PyStoreModelAdmin,
        CompareItem: PyStoreModelAdmin,
        NotificationTemplate: NotificationTemplateAdmin,
        WebhookEndpoint: WebhookEndpointAdmin,
        NotificationMessage: NotificationMessageAdmin,
        Notification: NotificationAdmin,
        ProductReview: ProductReviewAdmin,
        AuditLog: AuditLogAdmin,
        PluginState: PluginStateAdmin,
    }

    from apps.media.models import MediaFile

    registrations[MediaFile] = MediaFileAdmin

    for model, admin_class in registrations.items():
        try:
            admin_site.register(model, admin_class)
        except admin.sites.AlreadyRegistered:
            pass

