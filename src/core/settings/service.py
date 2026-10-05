import logging
from typing import Any

from core.exceptions import ApplicationError
from core.settings.definitions import (
    SettingDefinition,
    SettingDefinitionsRegistry,
    definitions_registry,
)
from core.settings.models import Setting

logger = logging.getLogger(__name__)

SENSITIVE_MASK = "******"


class SettingsError(ApplicationError):
    message = "Settings error"
    code = "settings_error"


def _validate_type(value: Any, value_type: type | None, key: str) -> Any:
    if value_type is None:
        return value
    if value_type is bool:
        if isinstance(value, bool):
            return value
        raise SettingsError(f"Setting {key!r} must be a boolean")
    if value_type in (int, float):
        if isinstance(value, bool) or not isinstance(value, value_type):
            raise SettingsError(f"Setting {key!r} must be of type {value_type.__name__}")
        return value
    if value_type is str:
        if not isinstance(value, str):
            raise SettingsError(f"Setting {key!r} must be a string")
        return value
    if value_type in (list, dict):
        if not isinstance(value, value_type):
            raise SettingsError(f"Setting {key!r} must be of type {value_type.__name__}")
        return value
    raise SettingsError(f"Unsupported setting type for {key!r}: {value_type!r}")


class SettingsService:
    def __init__(self, registry: SettingDefinitionsRegistry | None = None):
        self.registry = registry if registry is not None else definitions_registry
        self._cache: dict[tuple[str, str], Any] = {}

    def register(
        self,
        namespace: str,
        key: str,
        default: Any = None,
        value_type: type | None = None,
        sensitive: bool = False,
    ) -> SettingDefinition:
        definition = SettingDefinition(
            namespace=namespace,
            key=key,
            default=default,
            value_type=value_type,
            sensitive=sensitive,
        )
        self.registry.register(definition)
        self._cache.pop((namespace, key), None)
        return definition

    def get(self, namespace: str, key: str) -> Any:
        cache_key = (namespace, key)
        if cache_key in self._cache:
            return self._cache[cache_key]

        row = Setting.objects.filter(namespace=namespace, key=key).first()
        if row is not None:
            value = self._read_value(row)
        else:
            definition = self.registry.get(namespace, key)
            if definition is None:
                raise SettingsError(f"Setting {namespace}:{key} is not defined")
            value = definition.default

        self._cache[cache_key] = value
        return value

    def set(self, namespace: str, key: str, value: Any) -> Any:
        definition = self.registry.get(namespace, key)
        if definition is not None:
            value = _validate_type(value, definition.value_type, key)

        if definition is not None and definition.sensitive:
            from core.settings.crypto import encrypt_value

            stored = encrypt_value(str(value))
            is_sensitive = True
        else:
            stored = value
            is_sensitive = bool(definition and definition.sensitive)

        Setting.objects.update_or_create(
            namespace=namespace,
            key=key,
            defaults={"value": stored, "is_sensitive": is_sensitive},
        )
        self._cache.pop((namespace, key), None)
        logger.info("Setting %s:%s updated", namespace, key)
        return value

    def all(self, namespace: str, *, mask_sensitive: bool = True) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for definition in self.registry.for_namespace(namespace):
            result[definition.key] = definition.default
        for row in Setting.objects.filter(namespace=namespace):
            if row.is_sensitive and mask_sensitive:
                result[row.key] = SENSITIVE_MASK
            else:
                result[row.key] = self._read_value(row)
        return result

    def delete(self, namespace: str, key: str) -> None:
        Setting.objects.filter(namespace=namespace, key=key).delete()
        self._cache.pop((namespace, key), None)

    def clear_cache(self) -> None:
        self._cache.clear()

    def _read_value(self, row: Setting) -> Any:
        if row.is_sensitive:
            from core.settings.crypto import decrypt_value, is_encrypted

            if is_encrypted(row.value):
                return decrypt_value(row.value)
            return row.value
        return row.value


settings_service = SettingsService()


def get_setting(key: str, namespace: str = "global") -> Any:
    return settings_service.get(namespace, key)


def set_setting(key: str, value: Any, namespace: str = "global") -> Any:
    return settings_service.set(namespace, key, value)
