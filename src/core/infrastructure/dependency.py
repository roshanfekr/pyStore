import threading
from typing import Any, Callable


class DependencyContainer:
    def __init__(self):
        self._factories: dict[Any, Callable[[], Any]] = {}
        self._singleton_instances: dict[Any, Any] = {}
        self._singleton_flags: set[Any] = set()
        self._lock = threading.Lock()

    def register(self, key: Any, factory: Callable[[], Any], *, singleton: bool = False) -> None:
        with self._lock:
            self._factories[key] = factory
            self._singleton_flags.discard(key)
            self._singleton_instances.pop(key, None)
            if singleton:
                self._singleton_flags.add(key)

    def register_instance(self, key: Any, instance: Any) -> None:
        with self._lock:
            self._factories[key] = lambda: instance
            self._singleton_instances[key] = instance
            self._singleton_flags.add(key)

    def resolve(self, key: Any) -> Any:
        if key in self._singleton_flags and key in self._singleton_instances:
            return self._singleton_instances[key]
        factory = self._factories.get(key)
        if factory is None:
            raise KeyError(f"Dependency {key!r} is not registered")
        instance = factory()
        if key in self._singleton_flags:
            with self._lock:
                self._singleton_instances[key] = instance
        return instance

    def override(self, key: Any, factory: Callable[[], Any]) -> None:
        with self._lock:
            self._factories[key] = factory
            self._singleton_instances.pop(key, None)

    def unregister(self, key: Any) -> None:
        with self._lock:
            self._factories.pop(key, None)
            self._singleton_instances.pop(key, None)
            self._singleton_flags.discard(key)

    def clear(self) -> None:
        with self._lock:
            self._factories.clear()
            self._singleton_instances.clear()
            self._singleton_flags.clear()


container = DependencyContainer()
