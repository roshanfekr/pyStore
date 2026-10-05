import logging
from typing import Any, Callable

from django.core.cache import cache as default_backend

logger = logging.getLogger(__name__)

VERSION_KEY = "ns_version"


class CacheService:
    def __init__(self, backend=None, namespace: str = "app"):
        self._backend = backend if backend is not None else default_backend
        self.namespace = namespace

    def _version_key(self) -> str:
        return f"{self.namespace}:{VERSION_KEY}"

    def _key(self, key: str) -> str:
        version = self._backend.get(self._version_key()) or 1
        return f"{self.namespace}:v{version}:{key}"

    def get(self, key: str, default: Any = None) -> Any:
        return self._backend.get(self._key(key), default)

    def set(self, key: str, value: Any, timeout: int | None = None) -> None:
        self._backend.set(self._key(key), value, timeout)

    def delete(self, key: str) -> None:
        self._backend.delete(self._key(key))

    def get_or_set(self, key: str, factory: Callable[[], Any], timeout: int | None = None) -> Any:
        value = self.get(key)
        if value is None:
            value = factory()
            self.set(key, value, timeout)
        return value

    def clear_namespace(self) -> None:
        version = self._backend.get(self._version_key()) or 1
        self._backend.set(self._version_key(), version + 1, None)
        logger.info("Cache namespace %r invalidated", self.namespace)


cache_service = CacheService()
