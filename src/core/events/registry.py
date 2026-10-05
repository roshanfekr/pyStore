from core.events.base import DomainEvent


class EventRegistry:
    def __init__(self):
        self._events: dict[str, type[DomainEvent]] = {}

    def register(self, event_class: type[DomainEvent]) -> type[DomainEvent]:
        self._events[event_class.__name__] = event_class
        return event_class

    def get(self, event_name: str) -> type[DomainEvent] | None:
        return self._events.get(event_name)

    def all(self) -> dict[str, type[DomainEvent]]:
        return dict(self._events)


event_registry = EventRegistry()


def register_event(event_class: type[DomainEvent]) -> type[DomainEvent]:
    return event_registry.register(event_class)
