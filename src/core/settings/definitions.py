from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SettingDefinition:
    namespace: str
    key: str
    default: Any = None
    value_type: type | None = None
    sensitive: bool = False


class SettingDefinitionsRegistry:
    def __init__(self):
        self._definitions: dict[tuple[str, str], SettingDefinition] = {}

    def register(self, definition: SettingDefinition) -> None:
        self._definitions[(definition.namespace, definition.key)] = definition

    def get(self, namespace: str, key: str) -> SettingDefinition | None:
        return self._definitions.get((namespace, key))

    def for_namespace(self, namespace: str) -> list[SettingDefinition]:
        return [d for (ns, _), d in self._definitions.items() if ns == namespace]

    def all(self) -> list[SettingDefinition]:
        return list(self._definitions.values())


definitions_registry = SettingDefinitionsRegistry()
