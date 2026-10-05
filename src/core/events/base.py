import dataclasses
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class DomainEvent:
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def event_name(self) -> str:
        return type(self).__name__

    def to_payload(self) -> dict[str, Any]:
        payload = dataclasses.asdict(self)
        payload["occurred_at"] = self.occurred_at.isoformat()
        return payload

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "DomainEvent":
        kwargs = dict(payload)
        if isinstance(kwargs.get("occurred_at"), str):
            kwargs["occurred_at"] = datetime.fromisoformat(kwargs["occurred_at"])
        return cls(**kwargs)
