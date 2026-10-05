import uuid
from decimal import Decimal

from core.shipping import ShippingProvider

RATES = [
    {"code": "dummy_standard", "name": "Dummy Standard", "price": Decimal("5.0000")},
    {"code": "dummy_express", "name": "Dummy Express", "price": Decimal("15.0000")},
]


class DummyShippingProvider(ShippingProvider):
    code = "shipping_dummy"
    name = "Dummy Shipping Provider"

    def get_rates(self, context: dict) -> list[dict]:
        return [dict(rate) for rate in RATES]

    def calculate_shipping(self, context: dict) -> Decimal:
        code = (context or {}).get("code", "dummy_standard")
        for rate in RATES:
            if rate["code"] == code:
                return Decimal(rate["price"])
        raise ValueError(f"Unknown dummy shipping rate {code!r}")

    def create_shipment(self, order, **kwargs) -> dict:
        tracking = f"DUMMY-{uuid.uuid4().hex[:10].upper()}"
        return {
            "tracking_number": tracking,
            "carrier": self.code,
            "status": "created",
        }

    def cancel_shipment(self, shipment_id, **kwargs) -> dict:
        return {"shipment_id": str(shipment_id), "cancelled": True}

    def get_tracking(self, tracking_number: str) -> dict:
        return {
            "tracking_number": tracking_number,
            "status": "in_transit",
            "events": [
                {"at": "created", "description": "Shipment created"},
                {"at": "in_transit", "description": "Moving through dummy network"},
            ],
        }
