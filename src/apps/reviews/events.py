import dataclasses

from core.events import DomainEvent, register_event


@register_event
@dataclasses.dataclass(frozen=True)
class ReviewSubmitted(DomainEvent):
    review_id: str = ""
    product_id: str = ""
    user_id: str = ""
    rating: int = 0
    is_verified_purchase: bool = False


@register_event
@dataclasses.dataclass(frozen=True)
class ReviewModerated(DomainEvent):
    review_id: str = ""
    product_id: str = ""
    status: str = ""
    moderator_id: str = ""
