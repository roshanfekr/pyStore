from django.contrib import admin
from django.db.models import Count, Q, Sum
from django.template.response import TemplateResponse
from django.urls import path


class PyStoreAdminSite(admin.AdminSite):
    site_header = "pyStore Administration"
    site_title = "pyStore Admin"
    index_template = "admin_panel/dashboard.html"

    def dashboard_stats(self):
        from apps.cart.models import Cart
        from apps.catalog.models import Product
        from apps.identity.models import User
        from apps.inventory.models import InventoryItem
        from apps.orders.models import Order

        pending_orders = Order.objects.filter(status=Order.STATUS_PENDING).count()
        revenue = (
            Order.objects.filter(payment_status__in=[Order.PAYMENT_PAID, Order.PAYMENT_REFUNDED])
            .aggregate(total=Sum("total"))["total"]
            or 0
        )
        low_stock = [
            item
            for item in InventoryItem.objects.all()
            if item.stock_status in ("low_stock", "out_of_stock")
        ][:10]

        return {
            "total_orders": Order.objects.count(),
            "pending_orders": pending_orders,
            "revenue": revenue,
            "total_products": Product.objects.count(),
            "published_products": Product.objects.filter(is_published=True).count(),
            "total_customers": User.objects.filter(user_type="customer").count(),
            "active_carts": Cart.objects.filter(status=Cart.STATUS_ACTIVE).count(),
            "low_stock_items": low_stock,
        }

    def dashboard_view(self, request):
        from apps.orders.models import Order

        context = dict(
            self.each_context(request),
            stats=self.dashboard_stats(),
            orders_by_status=Order.objects.values("status").annotate(count=Count("id")),
        )
        return TemplateResponse(request, "admin_panel/dashboard.html", context)

    def reports_view(self, request):
        from apps.orders.models import Order
        from apps.pricing.models import Discount

        top_discounts = Discount.objects.order_by("-used_count")[:10]
        context = dict(
            self.each_context(request),
            revenue=Order.objects.aggregate(
                total_revenue=Sum("total", filter=~Q(status=Order.STATUS_CANCELLED))
            )["total_revenue"]
            or 0,
            refunded=Order.objects.filter(status=Order.STATUS_REFUNDED).aggregate(
                refunded_total=Sum("total")
            )["refunded_total"]
            or 0,
            orders_by_status=Order.objects.values("status").annotate(count=Count("id")),
            top_discounts=top_discounts,
        )
        return TemplateResponse(request, "admin_panel/reports.html", context)

    def plugins_view(self, request):
        from core.payments.registry import payment_gateway_registry
        from core.plugins.manager import PluginManager
        from core.shipping.registry import shipping_provider_registry

        manager = PluginManager()
        manager.discover_plugins()
        context = dict(
            self.each_context(request),
            plugins=manager.list_plugins(),
            errors=manager.errors,
            gateways=payment_gateway_registry.all(),
            shipping_providers=shipping_provider_registry.all(),
        )
        return TemplateResponse(request, "admin_panel/plugins.html", context)

    def get_urls(self):
        custom = [
            path("", self.admin_view(self.dashboard_view), name="index"),
            path("reports/", self.admin_view(self.reports_view), name="reports"),
            path("plugins/", self.admin_view(self.plugins_view), name="plugins"),
        ]
        remaining = [
            url
            for url in super().get_urls()
            if getattr(url, "name", "") not in ("index",) and not (
                getattr(url, "pattern", None) and str(url.pattern) == ""
            )
        ]
        return custom + remaining


admin_site = PyStoreAdminSite(name="pystore_admin")
