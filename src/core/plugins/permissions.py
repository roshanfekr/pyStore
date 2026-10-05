class PermissionRegistry:
    def __init__(self):
        self._by_plugin: dict[str, list[str]] = {}

    def register(self, plugin_id: str, permissions) -> None:
        current = self._by_plugin.setdefault(plugin_id, [])
        for permission in permissions:
            if permission not in current:
                current.append(permission)

    def unregister(self, plugin_id: str) -> None:
        self._by_plugin.pop(plugin_id, None)

    def for_plugin(self, plugin_id: str) -> list[str]:
        return list(self._by_plugin.get(plugin_id, []))

    def plugins(self) -> list[str]:
        return list(self._by_plugin.keys())

    def all(self) -> list[str]:
        unique: list[str] = []
        for permissions in self._by_plugin.values():
            for permission in permissions:
                if permission not in unique:
                    unique.append(permission)
        return unique


permission_registry = PermissionRegistry()
