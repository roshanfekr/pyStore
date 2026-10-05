from dataclasses import dataclass
from typing import Any

from core.exceptions import ApplicationError


@dataclass(frozen=True)
class Result:
    success: bool
    value: Any = None
    error: ApplicationError | None = None

    @classmethod
    def ok(cls, value: Any = None) -> "Result":
        return cls(success=True, value=value)

    @classmethod
    def fail(cls, error: ApplicationError) -> "Result":
        return cls(success=False, error=error)

    def __bool__(self) -> bool:
        return self.success
