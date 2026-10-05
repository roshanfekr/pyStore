from core.plugins.manifest import PluginRecord


class PluginRegistry:
    def __init__(self):
        self._records: dict[str, PluginRecord] = {}

    def add(self, record: PluginRecord) -> None:
        self._records[record.plugin_id] = record

    def get(self, plugin_id: str) -> PluginRecord | None:
        return self._records.get(plugin_id)

    def has(self, plugin_id: str) -> bool:
        return plugin_id in self._records

    def ids(self) -> list[str]:
        return list(self._records)

    def all(self) -> list[PluginRecord]:
        return list(self._records.values())

    def clear(self) -> None:
        self._records.clear()
