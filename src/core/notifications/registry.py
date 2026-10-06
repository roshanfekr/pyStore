
from core.notifications.interface import NotificationProvider


class NotificationProviderRegistry:
    def __init__(self):
        self._providers: dict[str, NotificationProvider] = {}

    def register(self, provider: NotificationProvider) -> NotificationProvider:
        if not provider.code:
            raise ValueError("Notification provider must define a code")
        if not provider.channel:
            raise ValueError("Notification provider must define a channel")
        self._providers[provider.code] = provider
        return provider

    def unregister(self, code: str) -> None:
        self._providers.pop(code, None)

    def get(self, code: str) -> NotificationProvider | None:
        return self._providers.get(code)

    def first_for_channel(self, channel: str) -> NotificationProvider | None:
        for provider in self._providers.values():
            if provider.channel == channel:
                return provider
        return None

    def for_channel(self, channel: str) -> list[NotificationProvider]:
        return [provider for provider in self._providers.values() if provider.channel == channel]

    def all(self) -> list[NotificationProvider]:
        return list(self._providers.values())


notification_provider_registry = NotificationProviderRegistry()
