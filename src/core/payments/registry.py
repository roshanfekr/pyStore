from core.payments.interface import PaymentGateway


class PaymentGatewayRegistry:
    def __init__(self):
        self._gateways: dict[str, PaymentGateway] = {}

    def register(self, gateway: PaymentGateway) -> PaymentGateway:
        self._gateways[gateway.code] = gateway
        return gateway

    def unregister(self, code: str) -> None:
        self._gateways.pop(code, None)

    def get(self, code: str) -> PaymentGateway | None:
        return self._gateways.get(code)

    def all(self) -> list[PaymentGateway]:
        return list(self._gateways.values())


payment_gateway_registry = PaymentGatewayRegistry()
