import dataclasses

from core.events import DomainEvent, register_event


@register_event
@dataclasses.dataclass(frozen=True)
class InventoryLowStock(DomainEvent):
    inventory_id: str = ""
    available_quantity: int = 0
    product_id: str = ""


@register_event
@dataclasses.dataclass(frozen=True)
class InventoryChanged(DomainEvent):
    inventory_id: str = ""
    transaction_type: str = ""
    stock_quantity: int = 0
    reserved_quantity: int = 0
