from core.exceptions import ValidationError


class OrderStateMachine:
    """Order lifecycle with validated transitions, extensible by plugins."""

    TRANSITIONS: dict[str, set[str]] = {
        "pending": {"processing", "cancelled", "refunded"},
        "processing": {"paid", "cancelled"},
        "paid": {"shipped", "cancelled", "refunded"},
        "shipped": {"completed", "refunded"},
        "completed": {"refunded"},
        "cancelled": set(),
        "refunded": set(),
    }

    @classmethod
    def register_status(cls, status: str, transitions: set[str] | None = None) -> None:
        cls.TRANSITIONS.setdefault(status, set(transitions or set()))

    @classmethod
    def register_transition(cls, from_status: str, to_status: str) -> None:
        cls.TRANSITIONS.setdefault(from_status, set()).add(to_status)

    @classmethod
    def reset(cls) -> None:
        cls.TRANSITIONS = {
            "pending": {"processing", "cancelled", "refunded"},
            "processing": {"paid", "cancelled"},
            "paid": {"shipped", "cancelled", "refunded"},
            "shipped": {"completed", "refunded"},
            "completed": {"refunded"},
            "cancelled": set(),
            "refunded": set(),
        }

    @classmethod
    def can_transition(cls, from_status: str, to_status: str) -> bool:
        return to_status in cls.TRANSITIONS.get(from_status, set())

    @classmethod
    def validate_transition(cls, from_status: str, to_status: str) -> None:
        if not cls.can_transition(from_status, to_status):
            raise ValidationError(
                f"Transition {from_status!r} -> {to_status!r} is not allowed",
                code="orders.invalid_transition",
            )


PAYMENT_TRANSITIONS: dict[str, set[str]] = {
    "pending": {"paid", "failed"},
    "failed": {"pending", "paid"},
    "paid": {"refunded"},
    "refunded": set(),
}

SHIPMENT_TRANSITIONS: dict[str, set[str]] = {
    "not_shipped": {"shipped"},
    "shipped": {"delivered"},
    "delivered": set(),
}


def validate_payment_transition(from_status: str, to_status: str) -> None:
    if to_status not in PAYMENT_TRANSITIONS.get(from_status, set()):
        raise ValidationError(
            f"Payment transition {from_status!r} -> {to_status!r} is not allowed",
            code="orders.invalid_payment_transition",
        )


def validate_shipment_transition(from_status: str, to_status: str) -> None:
    if to_status not in SHIPMENT_TRANSITIONS.get(from_status, set()):
        raise ValidationError(
            f"Shipment transition {from_status!r} -> {to_status!r} is not allowed",
            code="orders.invalid_shipment_transition",
        )
