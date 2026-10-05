import dataclasses

from core.events import DomainEvent, register_event


@register_event
@dataclasses.dataclass(frozen=True)
class CustomerRegistered(DomainEvent):
    email: str = ""
    user_id: str = ""


@register_event
@dataclasses.dataclass(frozen=True)
class PasswordReset(DomainEvent):
    email: str = ""
