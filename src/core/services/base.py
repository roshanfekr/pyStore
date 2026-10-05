import logging
from abc import ABC, abstractmethod
from typing import Any

from core.events import DomainEvent
from core.exceptions import ApplicationError, UnexpectedError
from core.services.result import Result

logger = logging.getLogger(__name__)


class BaseService(ABC):
    def __init__(self):
        self._events: list[DomainEvent] = []

    @abstractmethod
    def execute(self, *args, **kwargs) -> Any:
        ...

    def run(self, *args, **kwargs) -> Result:
        try:
            value = self.execute(*args, **kwargs)
        except ApplicationError as exc:
            logger.warning("Service %s failed: %s", type(self).__name__, exc.message)
            return Result.fail(exc)
        except Exception:
            logger.exception("Service %s raised an unexpected exception", type(self).__name__)
            return Result.fail(UnexpectedError())
        return Result.ok(value)

    def raise_event(self, event: DomainEvent) -> None:
        self._events.append(event)

    def collect_events(self) -> list[DomainEvent]:
        events, self._events = self._events, []
        return events
