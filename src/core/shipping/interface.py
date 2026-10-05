from abc import ABC, abstractmethod
from decimal import Decimal


class ShippingProvider(ABC):
    """Contract for shipping provider plugins."""

    code: str = ""
    name: str = ""

    @abstractmethod
    def get_rates(self, context: dict) -> list[dict]:
        ...

    @abstractmethod
    def calculate_shipping(self, context: dict) -> Decimal:
        ...

    @abstractmethod
    def create_shipment(self, order, **kwargs) -> dict:
        ...

    @abstractmethod
    def cancel_shipment(self, shipment_id, **kwargs) -> dict:
        ...

    @abstractmethod
    def get_tracking(self, tracking_number: str) -> dict:
        ...
