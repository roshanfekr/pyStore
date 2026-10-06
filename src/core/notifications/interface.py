from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class NotificationSendResult:
    successful: bool
    reference: str = ""
    message: str = ""
    raw: dict = field(default_factory=dict)


class NotificationProvider(ABC):
    """Contract for notification delivery providers.

    Providers are registered per channel (``email``, ``inapp``, ``webhook``,
    ``sms``) and can ship with the platform or be contributed by plugins.
    """

    code: str = ""
    name: str = ""
    channel: str = ""

    def configure(self, config: dict) -> None:
        self._config = dict(config or {})

    def get_configuration(self) -> dict:
        return dict(getattr(self, "_config", {}))

    def supports(self, channel: str) -> bool:
        return self.channel == channel

    @abstractmethod
    def send(self, message: Any) -> NotificationSendResult:
        """Deliver an outgoing notification message (duck-typed model)."""
        ...
