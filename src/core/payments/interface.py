from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import Decimal


@dataclass
class PaymentResult:
    successful: bool
    reference: str = ""
    message: str = ""
    raw: dict = field(default_factory=dict)


class PaymentGateway(ABC):
    """Contract for payment gateway plugins."""

    code: str = ""
    name: str = ""
    SUPPORTED_FEATURES: tuple = ()

    def configure(self, config: dict) -> None:
        self._config = dict(config or {})

    def supports(self, feature: str) -> bool:
        return feature in self.SUPPORTED_FEATURES

    def get_configuration(self) -> dict:
        return dict(getattr(self, "_config", {}))

    @abstractmethod
    def initialize_payment(self, order, *, amount: Decimal | None = None, **kwargs) -> PaymentResult:
        ...

    @abstractmethod
    def authorize(self, order, **kwargs) -> PaymentResult:
        ...

    @abstractmethod
    def capture(self, order, *, amount: Decimal | None = None, **kwargs) -> PaymentResult:
        ...

    @abstractmethod
    def void(self, order, **kwargs) -> PaymentResult:
        ...

    @abstractmethod
    def refund(self, order, amount: Decimal, **kwargs) -> PaymentResult:
        ...
