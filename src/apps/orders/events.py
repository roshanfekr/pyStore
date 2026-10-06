import dataclasses

from core.events import DomainEvent, register_event


@register_event
@dataclasses.dataclass(frozen=True)
class OrderCreated(DomainEvent):
    order_id: str = ""
    order_number: str = ""
    email: str = ""
    user_id: str = ""
    total: str = ""
    currency: str = ""


@register_event
@dataclasses.dataclass(frozen=True)
class OrderPaid(DomainEvent):
    order_id: str = ""
    order_number: str = ""
    email: str = ""
    user_id: str = ""
    total: str = ""
    currency: str = ""


@register_event
@dataclasses.dataclass(frozen=True)
class OrderShipped(DomainEvent):
    order_id: str = ""
    order_number: str = ""
    email: str = ""
    user_id: str = ""
    total: str = ""
    currency: str = ""


@register_event
@dataclasses.dataclass(frozen=True)
class OrderCancelled(DomainEvent):
    order_id: str = ""
    order_number: str = ""
    email: str = ""
    user_id: str = ""
    total: str = ""
    currency: str = ""
