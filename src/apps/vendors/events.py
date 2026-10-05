import dataclasses

from core.events import DomainEvent, register_event


@register_event
@dataclasses.dataclass(frozen=True)
class VendorCreated(DomainEvent):
    vendor_id: str = ""
    name: str = ""


@register_event
@dataclasses.dataclass(frozen=True)
class VendorStatusChanged(DomainEvent):
    vendor_id: str = ""
    new_status: str = ""
