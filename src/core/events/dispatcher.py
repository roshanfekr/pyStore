import logging
import threading
from typing import Callable

from core.events.base import DomainEvent

logger = logging.getLogger(__name__)

HandlerType = Callable[[DomainEvent], None]


class EventDispatcher:
    def __init__(self):
        self._handlers: dict[type, list[HandlerType]] = {}
        self._lock = threading.Lock()

    def subscribe(self, event_type: type, handler: HandlerType) -> None:
        with self._lock:
            self._handlers.setdefault(event_type, []).append(handler)

    def unsubscribe(self, event_type: type, handler: HandlerType) -> None:
        with self._lock:
            handlers = self._handlers.get(event_type, [])
            if handler in handlers:
                handlers.remove(handler)

    def get_handlers(self, event: DomainEvent) -> list[HandlerType]:
        return list(self._handlers.get(type(event), []))

    def dispatch(self, event: DomainEvent) -> None:
        for handler in self.get_handlers(event):
            try:
                handler(event)
            except Exception:
                logger.exception(
                    "Event handler %r failed for event %s (%s)",
                    getattr(handler, "__name__", handler),
                    event.event_name,
                    event.event_id,
                )

    def dispatch_async(self, event: DomainEvent) -> None:
        from core.events.tasks import dispatch_event_task

        dispatch_event_task.delay(event.event_name, event.to_payload())

    def dispatch_all(self, events) -> None:
        for event in events:
            self.dispatch(event)


dispatcher = EventDispatcher()


def subscribe(event_type: type):
    def decorator(handler: HandlerType) -> HandlerType:
        dispatcher.subscribe(event_type, handler)
        return handler

    return decorator


def register_handler(event_type: type, handler: HandlerType) -> None:
    dispatcher.subscribe(event_type, handler)
