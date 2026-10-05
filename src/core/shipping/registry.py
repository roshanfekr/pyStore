from core.shipping.interface import ShippingProvider


class ShippingProviderRegistry:
    def __init__(self):
        self._providers: dict[str, ShippingProvider] = {}

    def register(self, provider: ShippingProvider) -> ShippingProvider:
        self._providers[provider.code] = provider
        return provider

    def unregister(self, code: str) -> None:
        self._providers.pop(code, None)

    def get(self, code: str) -> ShippingProvider | None:
        return self._providers.get(code)

    def all(self) -> list[ShippingProvider]:
        return list(self._providers.values())


shipping_provider_registry = ShippingProviderRegistry()
