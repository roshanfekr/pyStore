from django.contrib import admin, messages
from django.template.response import TemplateResponse

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
from apps.stores.models import Store, StoreDomain
from apps.vendors.models import Vendor, VendorUser
from core.exceptions import ValidationError

CANCELLABLE_STATUSES = (Order.STATUS_PENDING, Order.STATUS_PROCESSING, Order.STATUS_PAID)


class ReadOnlyAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


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


class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "parent", "is_active", "ordering")
    list_filter = ("is_active", "parent")
    search_fields = ("name", "slug")


class BrandAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active")
    search_fields = ("name",)
    list_filter = ("is_active",)


class TagAdmin(admin.ModelAdmin):
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


class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "store", "product_type", "price", "stock_quantity", "is_published")
    list_filter = ("product_type", "is_published", "store", "brand")
    search_fields = ("name", "slug", "sku", "description")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    inlines = [ProductVariantInline, ProductImageInline, ProductSpecificationInline, ProductSEOInline]
    actions = ["publish_products", "unpublish_products"]

    @admin.action(description="Publish selected products")
    def publish_products(self, request, queryset):
        updated = queryset.update(is_published=True)
        self.message_user(request, f"{updated} product(s) published.")

    @admin.action(description="Unpublish selected products")
    def unpublish_products(self, request, queryset):
        updated = queryset.update(is_published=False)
        self.message_user(request, f"{updated} product(s) unpublished.")


class ProductAttributeAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "value_type", "is_variant_option")
    list_filter = ("value_type",)
    search_fields = ("name", "slug")


class ProductAttributeValueAdmin(admin.ModelAdmin):
    list_display = ("attribute", "value", "position")
    list_filter = ("attribute",)


class WarehouseAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "store", "city", "is_default")
    search_fields = ("name", "code")


class WarehouseLocationAdmin(admin.ModelAdmin):
    list_display = ("warehouse", "code")
    search_fields = ("code",)


class InventoryItemAdmin(admin.ModelAdmin):
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


class UserAdmin(admin.ModelAdmin):
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


class CustomerAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "phone", "is_deleted")
    search_fields = ("user__email", "phone")
    list_filter = ("is_deleted",)


class RoleAdmin(admin.ModelAdmin):
    list_display = ("name", "is_system", "display_permissions")
    search_fields = ("name",)
    filter_horizontal = ("permissions", "users")

    @admin.display(description="Permissions")
    def display_permissions(self, obj):
        return ", ".join(p.codename for p in obj.permissions.all()[:5])


class PermissionAdmin(admin.ModelAdmin):
    list_display = ("codename", "source", "display_name")
    list_filter = ("source",)
    search_fields = ("codename",)


class OrderAdmin(admin.ModelAdmin):
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
        if not request.user.has_perm("orders.cancel"):
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


class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("order", "product_name", "sku", "quantity", "unit_price", "line_total")
    search_fields = ("product_name", "sku", "order__number")


class OrderStatusLogAdmin(ReadOnlyAdmin):
    list_display = ("order", "status_type", "from_value", "to_value", "actor", "created_at")
    list_filter = ("status_type",)
    date_hierarchy = "created_at"


class RefundAdmin(ReadOnlyAdmin):
    list_display = ("order", "amount", "reason", "actor", "created_at")
    date_hierarchy = "created_at"


class ReturnRequestAdmin(admin.ModelAdmin):
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


class PriceListAdmin(admin.ModelAdmin):
    list_display = ("name", "store", "role", "customer", "priority", "is_active")
    list_filter = ("is_active",)
    inlines = []


class PriceListEntryAdmin(admin.ModelAdmin):
    list_display = ("price_list", "product", "variant", "price", "min_quantity", "max_quantity")


class ScheduledPriceAdmin(admin.ModelAdmin):
    list_display = ("product", "variant", "price", "start_at", "end_at", "is_active")
    list_filter = ("is_active",)


class DiscountAdmin(admin.ModelAdmin):
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


class TaxClassAdmin(admin.ModelAdmin):
    list_display = ("name", "is_default")


class TaxRateAdmin(admin.ModelAdmin):
    list_display = ("name", "tax_class", "rate", "country", "state", "is_active")
    list_filter = ("tax_class", "is_active")


class StoreAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_default", "is_active", "default_currency")
    search_fields = ("name", "slug")


class StoreDomainAdmin(admin.ModelAdmin):
    list_display = ("domain", "store", "is_primary", "ssl_enabled")
    search_fields = ("domain",)


class VendorAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "status", "store", "owner")
    list_filter = ("status",)
    search_fields = ("name", "slug")


class VendorUserAdmin(admin.ModelAdmin):
    list_display = ("vendor", "user", "is_admin")


class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "is_active")
    list_filter = ("is_active",)


class ShippingMethodAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "store", "flat_price", "is_active")
    list_filter = ("store", "is_active")


class PageAdmin(admin.ModelAdmin):
    list_display = ("title", "slug", "is_published")
    search_fields = ("title", "slug")
    list_filter = ("is_published",)


class BlogPostAdmin(admin.ModelAdmin):
    list_display = ("title", "slug", "author", "is_published", "published_at")
    search_fields = ("title",)
    list_filter = ("is_published",)


class MenuAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name",)


class WidgetAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "widget_type", "is_active")
    list_filter = ("widget_type", "is_active")


class ContentBlockAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active")
    search_fields = ("name", "slug")


class MediaFileAdmin(admin.ModelAdmin):
    list_display = ("original_name", "media_type", "size", "uploaded_by", "created_at")
    list_filter = ("media_type",)
    search_fields = ("original_name",)

    def has_add_permission(self, request):
        return False


def register_all(admin_site):
    registrations = {
        Category: CategoryAdmin,
        Brand: BrandAdmin,
        Tag: TagAdmin,
        Product: ProductAdmin,
        ProductAttribute: ProductAttributeAdmin,
        ProductAttributeValue: ProductAttributeValueAdmin,
        ProductBundleItem: admin.ModelAdmin,
        ProductDownload: admin.ModelAdmin,
        ProductRelation: admin.ModelAdmin,
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
        ReturnRequestItem: admin.ModelAdmin,
        OrderNote: admin.ModelAdmin,
        OrderAddress: admin.ModelAdmin,
        PriceList: PriceListAdmin,
        PriceListEntry: PriceListEntryAdmin,
        ScheduledPrice: ScheduledPriceAdmin,
        Discount: DiscountAdmin,
        DiscountUsage: DiscountUsageAdmin,
        TaxClass: TaxClassAdmin,
        TaxRate: TaxRateAdmin,
        CustomerTaxInfo: admin.ModelAdmin,
        ProductTaxSetting: admin.ModelAdmin,
        Store: StoreAdmin,
        StoreDomain: StoreDomainAdmin,
        Vendor: VendorAdmin,
        VendorUser: VendorUserAdmin,
        PaymentMethod: PaymentMethodAdmin,
        ShippingMethod: ShippingMethodAdmin,
        Page: PageAdmin,
        BlogCategory: admin.ModelAdmin,
        BlogPost: BlogPostAdmin,
        Menu: MenuAdmin,
        MenuItem: admin.ModelAdmin,
        Widget: WidgetAdmin,
        ContentBlock: ContentBlockAdmin,
        Cart: admin.ModelAdmin,
        CartItem: admin.ModelAdmin,
        WishlistItem: admin.ModelAdmin,
        CompareItem: admin.ModelAdmin,
    }

    from apps.media.models import MediaFile

    registrations[MediaFile] = MediaFileAdmin

    for model, admin_class in registrations.items():
        try:
            admin_site.register(model, admin_class)
        except admin.sites.AlreadyRegistered:
            pass
