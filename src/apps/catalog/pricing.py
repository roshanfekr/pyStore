from decimal import Decimal
from typing import Callable

from apps.catalog.models import Product, ProductVariant

PriceProvider = Callable[[Product, "ProductVariant | None", dict], Decimal]

_FOUR_PLACES = Decimal("0.0001")


class PricingRegistry:
    """Extension point for the future Pricing Engine (Phase 08).

    Without a registered provider, the stored base price is returned.
    After the provider runs, price modifiers registered by enabled plugins
    are applied in plugin id order.
    """

    def __init__(self):
        self._provider: PriceProvider | None = None

    def register(self, provider: PriceProvider) -> None:
        self._provider = provider

    def reset(self) -> None:
        self._provider = None

    def _apply_plugin_modifiers(self, product, variant, price, context) -> Decimal:
        from core.plugins.manager import PluginManager

        manager = PluginManager()
        try:
            manager.discover_plugins()
        except Exception:
            return price
        for _plugin_id, modifier in manager.enabled_price_modifiers():
            try:
                new_price = modifier(product, variant, price, context)
            except Exception:
                continue
            if new_price is not None:
                price = Decimal(new_price)
        return price.quantize(_FOUR_PLACES)

    def resolve(
        self,
        product: Product,
        variant: ProductVariant | None = None,
        context: dict | None = None,
    ) -> Decimal:
        context = context or {}
        if self._provider is not None:
            price = self._provider(product, variant, context)
        elif variant is not None:
            price = variant.price
        elif product.price is not None:
            price = product.price
        else:
            raise ValueError(f"Product {product.pk} has no price configured")
        return self._apply_plugin_modifiers(product, variant, price, context)


pricing_registry = PricingRegistry()
