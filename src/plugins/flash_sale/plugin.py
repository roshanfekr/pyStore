from core.plugins.base import Plugin
from plugins.flash_sale.admin_urls import admin_urlpatterns
from plugins.flash_sale.services import active_sales, apply_flash_sale_price
from plugins.flash_sale.views_data import sale_rows


class FlashSalePlugin(Plugin):
    def get_price_modifiers(self):
        return [apply_flash_sale_price]

    def get_storefront_hooks(self):
        return {"home_middle": ["flash_sale/section.html"]}

    def get_hook_context(self, hook_name: str) -> dict:
        from django.utils import timezone

        if hook_name != "home_middle":
            return {}
        sales = active_sales()[:8]
        next_end = min((sale.end_at for sale in sales), default=None)
        return {
            "sales": sale_rows(sales),
            "heading": "Flash sale",
            "next_end": next_end.strftime("%Y-%m-%d %H:%M") if next_end else timezone.now().strftime("%Y-%m-%d"),
        }

    def get_admin_urls(self):
        return list(admin_urlpatterns)
