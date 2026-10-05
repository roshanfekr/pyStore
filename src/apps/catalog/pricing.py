from decimal import Decimal
from typing import Callable

from apps.catalog.models import Product, ProductVariant

PriceProvider = Callable[[Product, "ProductVariant | None", dict], Decimal]


class PricingRegistry:
    """Extension point for the future Pricing Engine (Phase 08).

    Without a registered provider, the stored base price is returned.
    """

    def __init__(self):
        self._provider: PriceProvider | None = None

    def register(self, provider: PriceProvider) -> None:
        self._provider = provider

    def reset(self) -> None:
        self._provider = None

    def resolve(
        self,
        product: Product,
        variant: ProductVariant | None = None,
        context: dict | None = None,
    ) -> Decimal:
        context = context or {}
        if self._provider is not None:
            return self._provider(product, variant, context)
        if variant is not None:
            return variant.price
        if product.price is not None:
            return product.price
        raise ValueError(f"Product {product.pk} has no price configured")


pricing_registry = PricingRegistry()
