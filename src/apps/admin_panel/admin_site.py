from django.contrib import admin, messages
from django.db.models import Count, Q, Sum
from django.http import Http404
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import path, reverse

from core.plugins.exceptions import PluginNotFoundError
from core.plugins.manager import PluginManager
from core.plugins.models import STATUS_ENABLED


def _plugin_manager() -> PluginManager:
    manager = PluginManager()
    manager.discover_plugins()
    return manager


def _plugin_settings_items() -> list[dict]:
    """Sidebar entries: enabled plugins with a settings schema or admin pages."""
    try:
        manager = _plugin_manager()
    except Exception:
        return []
    items = []
    for info in manager.list_plugins():
        if info.status != STATUS_ENABLED:
            continue
        try:
            plugin = manager.get_class(info.plugin_id)()
        except Exception:
            continue
        if plugin.get_settings_schema():
            items.append(
                {
                    "plugin_id": info.plugin_id,
                    "name": info.name,
                    "url": reverse("pystore_admin:plugin_settings", args=[info.plugin_id]),
                }
            )
        admin_urls = list(plugin.get_admin_urls())
        if admin_urls:
            items.append(
                {
                    "plugin_id": info.plugin_id,
                    "name": f"{info.name} — manage",
                    "url": reverse(f"pystore_admin:{admin_urls[0].name}"),
                }
            )
    return items


def _coerce_settings_values(schema: dict, post) -> dict:
    values = {}
    for key, field in schema.items():
        field_type = field.get("type", "string")
        if field_type == "boolean":
            values[key] = post.get(key) == "on"
        elif field_type == "integer":
            raw = (post.get(key) or "").strip()
            try:
                values[key] = int(raw)
            except ValueError:
                values[key] = 0
        else:
            values[key] = post.get(key, "")
    return values


def _upgradable_plugin_ids(manager: PluginManager) -> set[str]:
    from packaging.version import Version

    upgradable = set()
    for info in manager.list_plugins():
        record = manager.registry.get(info.plugin_id)
        if record is None:
            continue
        try:
            if info.status != "not_installed" and Version(record.manifest.version) > Version(info.version):
                upgradable.add(info.plugin_id)
        except Exception:
            continue
    return upgradable


class PyStoreAdminSite(admin.AdminSite):
    site_header = "pyStore Administration"
    site_title = "pyStore Admin"
    index_template = "admin_panel/dashboard.html"

    # Apps hidden from the sidebar; their pages stay reachable by URL.
    hidden_sidebar_app_labels: set[str] = {"notifications"}

    def each_context(self, request):
        from apps.stores.services import get_active_language_code, get_active_languages

        context = super().each_context(request)
        context["plugin_settings_items"] = _plugin_settings_items()
        context["admin_languages"] = get_active_languages()
        context["admin_active_language"] = get_active_language_code(
            request.COOKIES.get("pystore_language")
        )
        context["available_apps"] = [
            app
            for app in context.get("available_apps", [])
            if app.get("app_label") not in self.hidden_sidebar_app_labels
        ]
        return context

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
        from apps.storefront.themes import (
            get_active_theme_name,
            get_theme_manifest,
            list_themes,
        )
        from core.payments.registry import payment_gateway_registry
        from core.plugins import theme_discovery
        from core.shipping.registry import shipping_provider_registry

        manager = _plugin_manager()

        themes = []
        active_theme = get_active_theme_name()
        for slug in list_themes():
            theme_dir = theme_discovery.find_theme_dir(slug)
            source = "built-in" if theme_dir and theme_dir.parent == theme_discovery.THEMES_DIR else "plugin"
            themes.append(
                {
                    "name": get_theme_manifest(slug).get("name", slug),
                    "slug": slug,
                    "source": source,
                    "active": slug == active_theme,
                }
            )

        if request.method == "POST":
            self._handle_plugin_action(request, manager)
            return redirect("pystore_admin:plugins")

        plugin_infos = manager.list_plugins()

        action_links: dict[str, dict] = {}
        for plugin_id, patterns in manager.enabled_admin_urls():
            if patterns:
                action_links[plugin_id] = {
                    "label": "Manage",
                    "url": reverse(f"pystore_admin:{patterns[0].name}"),
                }

        context = dict(
            self.each_context(request),
            plugins=plugin_infos,
            errors=manager.errors,
            upgradable=_upgradable_plugin_ids(manager),
            gateways=payment_gateway_registry.all(),
            shipping_providers=shipping_provider_registry.all(),
            settings_ready={
                info.plugin_id
                for info in plugin_infos
                if manager.plugin_has_settings_schema(info.plugin_id)
            },
            action_links=action_links,
            themes=themes,
        )
        return TemplateResponse(request, "admin_panel/plugins.html", context)

    def plugin_settings_view(self, request, plugin_id: str):
        manager = _plugin_manager()
        try:
            info = manager.get_plugin(plugin_id)
            schema = manager.get_class(plugin_id)().get_settings_schema()
        except PluginNotFoundError as exc:
            raise Http404(str(exc)) from exc

        if not schema:
            messages.info(request, f"Plugin {plugin_id!r} has no configurable settings.")
            return redirect("pystore_admin:plugins")

        if request.method == "POST":
            if not request.user.is_superuser:
                messages.error(request, "Only superusers can change plugin settings.")
                return redirect("pystore_admin:plugin_settings", plugin_id=plugin_id)

            manager.set_settings(plugin_id, _coerce_settings_values(schema, request.POST))
            messages.success(request, f"Settings for {info.name!r} saved.")
            return redirect("pystore_admin:plugin_settings", plugin_id=plugin_id)

        current = manager.get_settings(plugin_id)
        fields = [
            {
                "key": key,
                "label": field.get("label", key),
                "type": field.get("type", "string"),
                "help": field.get("help", ""),
                "value": current.get(key, ""),
            }
            for key, field in schema.items()
        ]
        context = dict(
            self.each_context(request),
            plugin=info,
            fields=fields,
        )
        return TemplateResponse(request, "admin_panel/plugin_settings.html", context)

    def _handle_plugin_action(self, request, manager: PluginManager) -> None:
        if not request.user.is_superuser:
            messages.error(request, "Only superusers can manage plugins.")
            return

        plugin_id = request.POST.get("plugin_id", "")
        action = request.POST.get("action", "")

        handlers = {
            "install": (manager.install_plugin, "installed"),
            "enable": (manager.enable_plugin, "enabled"),
            "disable": (manager.disable_plugin, "disabled"),
            "uninstall": (manager.uninstall_plugin, "uninstalled"),
            "upgrade": (manager.upgrade_plugin, "upgraded"),
        }
        if action not in handlers:
            messages.error(request, f"Unknown plugin action: {action!r}")
            return

        try:
            handlers[action][0](plugin_id, actor=request.user)
        except Exception as exc:
            messages.error(request, str(getattr(exc, "message", exc)))
            return

        messages.success(request, f"Plugin {plugin_id!r} {handlers[action][1]} successfully.")

    def get_urls(self):
        from django.urls import include

        plugin_urls = []
        try:
            mounted_admin_urls = _plugin_manager().discovered_admin_urls()
        except Exception:
            mounted_admin_urls = []
        for plugin_id, patterns in mounted_admin_urls:
            plugin_urls.append(path(f"plugins/{plugin_id}/", include(patterns)))

        custom = [
            path("", self.admin_view(self.dashboard_view), name="index"),
            path("reports/", self.admin_view(self.reports_view), name="reports"),
            path("plugins/", self.admin_view(self.plugins_view), name="plugins"),
            path(
                "plugins/<str:plugin_id>/settings/",
                self.admin_view(self.plugin_settings_view),
                name="plugin_settings",
            ),
        ] + plugin_urls
        remaining = [
            url
            for url in super().get_urls()
            if getattr(url, "name", "") not in ("index",) and not (
                getattr(url, "pattern", None) and str(url.pattern) == ""
            )
        ]
        return custom + remaining


admin_site = PyStoreAdminSite(name="pystore_admin")
