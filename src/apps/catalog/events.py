import dataclasses

from core.events import DomainEvent, register_event


@register_event
@dataclasses.dataclass(frozen=True)
class ProductCreated(DomainEvent):
    product_id: str = ""
    name: str = ""
    store_id: str = ""


@register_event
@dataclasses.dataclass(frozen=True)
class ProductPublished(DomainEvent):
    product_id: str = ""
    name: str = ""
