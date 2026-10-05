import uuid
from decimal import Decimal

from core.payments import PaymentGateway, PaymentResult


class DummyGateway(PaymentGateway):
    code = "payment_dummy"
    name = "Dummy Payment Gateway"
    SUPPORTED_FEATURES = ("authorize", "capture", "void", "refund")

    def _reference(self, prefix: str) -> str:
        return f"{prefix}-{uuid.uuid4().hex[:12].upper()}"

    def initialize_payment(self, order, *, amount: Decimal | None = None, **kwargs) -> PaymentResult:
        reference = self._reference("DPAY")
        return PaymentResult(
            successful=True,
            reference=reference,
            message="Redirect the customer to the dummy payment page",
            raw={"redirect_url": f"https://dummy.example/pay/{reference}"},
        )

    def authorize(self, order, **kwargs) -> PaymentResult:
        return PaymentResult(successful=True, reference=self._reference("DAUTH"))

    def capture(self, order, *, amount: Decimal | None = None, **kwargs) -> PaymentResult:
        captured = amount or (order.total if order is not None else None)
        return PaymentResult(
            successful=True,
            reference=self._reference("DCAP"),
            raw={"captured_amount": str(captured) if captured else None},
        )

    def void(self, order, **kwargs) -> PaymentResult:
        return PaymentResult(successful=True, reference=self._reference("DVOID"))

    def refund(self, order, amount: Decimal, **kwargs) -> PaymentResult:
        return PaymentResult(
            successful=True,
            reference=self._reference("DREF"),
            raw={"refunded_amount": str(amount)},
        )
