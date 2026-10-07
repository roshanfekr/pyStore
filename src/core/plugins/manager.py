from dataclasses import dataclass, field
from pathlib import Path

from django.conf import settings
from packaging.version import Version

from core.events import EventDispatcher, dispatcher
from core.infrastructure import DependencyContainer
from core.infrastructure.dependency import container as global_container
from core.plugins.exceptions import (
    PluginAlreadyInstalledError,
    PluginDependencyError,
    PluginError,
    PluginNotFoundError,
    PluginNotInstalledError,
    PluginVersionError,
)
from core.plugins.loader import load_entry_class
from core.plugins.manifest import PluginManifest, PluginRecord, load_manifest
from core.plugins.models import (
    STATUS_DISABLED,
    STATUS_ENABLED,
    STATUS_INSTALLED,
    PluginState,
)
from core.plugins.permissions import PermissionRegistry, permission_registry
from core.plugins.registry import PluginRegistry


@dataclass
class PluginInfo:
    plugin_id: str
    name: str
    version: str
    status: str
    description: str = ""
    author: str = ""
    dependencies: tuple[str, ...] = field(default=())


class PluginManager:
    def __init__(
        self,
        plugins_dir=None,
        services_container: DependencyContainer | None = None,
        event_dispatcher: EventDispatcher | None = None,
        permissions: PermissionRegistry | None = None,
    ):
        self.plugins_dir = Path(plugins_dir) if plugins_dir else Path(settings.BASE_DIR) / "plugins"
        self.services = services_container if services_container is not None else global_container
        self.event_dispatcher = event_dispatcher if event_dispatcher is not None else dispatcher
        self.permissions = permissions if permissions is not None else permission_registry
        self.registry = PluginRegistry()
        self.errors: list[str] = []
        self._event_registrations: dict[str, list[tuple[type, object]]] = {}
        self._service_keys: dict[str, list] = {}
        self._permission_plugins: set[str] = set()
        self._gateway_codes: dict[str, list[str]] = {}
        self._shipping_provider_codes: dict[str, list[str]] = {}
        self._notification_provider_codes: dict[str, list[str]] = {}

    def discover_plugins(self) -> list[str]:
        self.registry.clear()
        self.errors = []
        if not self.plugins_dir.exists():
            return []

        for entry in sorted(self.plugins_dir.iterdir()):
            if not entry.is_dir():
                continue
            manifest_file = entry / "plugin.json"
            if not manifest_file.exists():
                continue
            try:
                manifest = load_manifest(manifest_file)
            except PluginError as exc:
                self.errors.append(f"{entry.name}: {exc.message}")
                continue
            if self.registry.has(manifest.plugin_id):
                self.errors.append(f"{entry.name}: duplicate plugin id {manifest.plugin_id!r}")
                continue
            self.registry.add(PluginRecord(manifest=manifest, path=entry))
        return self.registry.ids()

    def get_class(self, plugin_id: str) -> type:
        return load_entry_class(self._require_record(plugin_id))

    def list_plugins(self) -> list[PluginInfo]:
        states = {state.plugin_id: state for state in PluginState.objects.all()}
        infos = []
        for record in self.registry.all():
            manifest = record.manifest
            state = states.pop(manifest.plugin_id, None)
            infos.append(
                PluginInfo(
                    plugin_id=manifest.plugin_id,
                    name=manifest.name,
                    version=state.version if state else str(manifest.version),
                    status=state.status if state else "not_installed",
                    description=manifest.description,
                    author=manifest.author,
                    dependencies=manifest.dependencies,
                )
            )
        for state in states.values():
            infos.append(
                PluginInfo(
                    plugin_id=state.plugin_id,
                    name=state.name,
                    version=state.version,
                    status=state.status,
                    description="(plugin directory not found)",
                )
            )
        infos.sort(key=lambda info: info.plugin_id)
        return infos

    def get_plugin(self, plugin_id: str) -> PluginInfo:
        for info in self.list_plugins():
            if info.plugin_id == plugin_id:
                return info
        raise PluginNotFoundError(f"Plugin {plugin_id!r} is not discovered")

    def install_plugin(self, plugin_id: str, *, actor=None) -> PluginState:
        record = self._require_record(plugin_id)
        manifest = record.manifest

        if self._state(plugin_id) is not None:
            raise PluginAlreadyInstalledError(f"Plugin {plugin_id!r} is already installed")

        if manifest.minimum_core_version and manifest.minimum_core_version > Version(core_version()):
            raise PluginVersionError(
                f"Plugin {plugin_id!r} requires core >= {manifest.minimum_core_version}, "
                f"but core version is {core_version()}"
            )

        for dependency in manifest.dependencies:
            if self._state(dependency) is None:
                raise PluginDependencyError(
                    f"Dependency {dependency!r} of plugin {plugin_id!r} is not installed"
                )

        plugin = self.get_class(plugin_id)()
        try:
            plugin.on_install()
        except Exception as exc:
            raise PluginError(f"Installation of plugin {plugin_id!r} failed: {exc}") from exc

        state = PluginState.objects.create(
            plugin_id=plugin_id,
            name=manifest.name,
            version=str(manifest.version),
            status=STATUS_INSTALLED,
        )
        self._audit(actor, "plugin.installed", plugin_id)
        return state

    def uninstall_plugin(self, plugin_id: str, *, actor=None) -> None:
        state = self._require_state(plugin_id)

        if state.status != STATUS_DISABLED:
            raise PluginError(f"Plugin {plugin_id!r} must be disabled before uninstalling")

        for other in PluginState.objects.exclude(plugin_id=plugin_id):
            if other.status in (STATUS_INSTALLED, STATUS_ENABLED):
                other_manifest = self._manifest_of(other.plugin_id)
                if other_manifest and plugin_id in other_manifest.dependencies:
                    raise PluginDependencyError(
                        f"Plugin {plugin_id!r} cannot be uninstalled: "
                        f"installed plugin {other.plugin_id!r} depends on it"
                    )

        if self.registry.get(plugin_id) is not None:
            plugin = self.get_class(plugin_id)()
            try:
                plugin.on_uninstall()
            except Exception as exc:
                raise PluginError(f"Uninstalling plugin {plugin_id!r} failed: {exc}") from exc

        self._unregister_runtime(plugin_id)
        state.delete()
        self._audit(actor, "plugin.uninstalled", plugin_id)

    def enable_plugin(self, plugin_id: str, *, actor=None) -> PluginState:
        state = self._require_state(plugin_id)

        if state.status == STATUS_ENABLED:
            raise PluginError(f"Plugin {plugin_id!r} is already enabled")

        for dependency in self._require_record(plugin_id).manifest.dependencies:
            dependency_state = self._state(dependency)
            if dependency_state is None or dependency_state.status != STATUS_ENABLED:
                raise PluginDependencyError(
                    f"Dependency {dependency!r} of plugin {plugin_id!r} is not enabled"
                )

        plugin = self.get_class(plugin_id)()
        try:
            plugin.on_enable()
        except Exception as exc:
            raise PluginError(f"Enabling plugin {plugin_id!r} failed: {exc}") from exc

        self._register_runtime(plugin_id, plugin)
        state.status = STATUS_ENABLED
        state.save()
        self._audit(actor, "plugin.enabled", plugin_id)
        return state

    def disable_plugin(self, plugin_id: str, *, actor=None) -> PluginState:
        state = self._require_state(plugin_id)

        if state.status != STATUS_ENABLED:
            raise PluginError(f"Plugin {plugin_id!r} is not enabled")

        for other in PluginState.objects.exclude(plugin_id=plugin_id).filter(status=STATUS_ENABLED):
            other_manifest = self._manifest_of(other.plugin_id)
            if other_manifest and plugin_id in other_manifest.dependencies:
                raise PluginDependencyError(
                    f"Plugin {plugin_id!r} cannot be disabled: "
                    f"enabled plugin {other.plugin_id!r} depends on it"
                )

        plugin = self.get_class(plugin_id)()
        try:
            plugin.on_disable()
        except Exception as exc:
            raise PluginError(f"Disabling plugin {plugin_id!r} failed: {exc}") from exc

        self._unregister_runtime(plugin_id)
        state.status = STATUS_DISABLED
        state.save()
        self._audit(actor, "plugin.disabled", plugin_id)
        return state

    def upgrade_plugin(self, plugin_id: str, *, actor=None) -> PluginState:
        state = self._require_state(plugin_id)
        manifest = self._require_record(plugin_id).manifest
        old_version = Version(state.version)

        if manifest.version <= old_version:
            raise PluginVersionError(
                f"Discovered version {manifest.version} of plugin {plugin_id!r} is not newer "
                f"than installed version {old_version}"
            )

        plugin = self.get_class(plugin_id)()
        try:
            plugin.on_upgrade(str(old_version), str(manifest.version))
        except Exception as exc:
            raise PluginError(f"Upgrading plugin {plugin_id!r} failed: {exc}") from exc

        state.version = str(manifest.version)
        state.save()
        self._audit(
            actor,
            "plugin.upgraded",
            plugin_id,
            before={"version": str(old_version)},
            after={"version": str(manifest.version)},
        )
        return state

    def get_settings(self, plugin_id: str) -> dict:
        plugin = self.get_class(plugin_id)()
        defaults = plugin.get_settings_defaults()
        state = self._state(plugin_id)
        stored = state.settings if state else {}
        return {**defaults, **stored}

    def enabled_storefront_hooks(self, hook_name: str) -> list[tuple[str, str]]:
        """(plugin_id, template_name) pairs for enabled plugins on a hook."""
        pairs: list[tuple[str, str]] = []
        for info in self.list_plugins():
            if info.status != STATUS_ENABLED:
                continue
            try:
                plugin = self.get_class(info.plugin_id)()
                hook_templates = plugin.get_storefront_hooks()
            except Exception:
                continue
            for template_name in dict(hook_templates or {}).get(hook_name, []):
                pairs.append((info.plugin_id, template_name))
        return pairs

    def plugin_has_settings_schema(self, plugin_id: str) -> bool:
        try:
            plugin = self.get_class(plugin_id)()
        except PluginError:
            return False
        return bool(plugin.get_settings_schema())

    def enabled_price_modifiers(self) -> list[tuple[str, object]]:
        """(plugin_id, modifier) pairs of enabled plugins, in plugin id order."""
        modifiers: list[tuple[str, object]] = []
        for info in self.list_plugins():
            if info.status != STATUS_ENABLED:
                continue
            try:
                plugin = self.get_class(info.plugin_id)()
                modifiers.extend(
                    (info.plugin_id, modifier)
                    for modifier in plugin.get_price_modifiers()
                )
            except Exception:
                continue
        return modifiers

    def discovered_admin_urls(self) -> list[tuple[str, list]]:
        """(plugin_id, urlpatterns) for all discovered plugins exposing admin pages.

        Mounting is independent of the enabled state so URL reversing is stable;
        views must check `is_plugin_enabled` at request time.
        """
        pairs: list[tuple[str, list]] = []
        for record in self.registry.all():
            try:
                plugin = self.get_class(record.plugin_id)()
                urls = list(plugin.get_admin_urls())
            except Exception:
                continue
            if urls:
                pairs.append((record.plugin_id, urls))
        return pairs

    def is_plugin_enabled(self, plugin_id: str) -> bool:
        state = PluginState.objects.filter(plugin_id=plugin_id).first()
        return state is not None and state.status == STATUS_ENABLED

    def enabled_admin_urls(self) -> list[tuple[str, list]]:
        """(plugin_id, urlpatterns) for enabled plugins exposing admin pages."""
        pairs: list[tuple[str, list]] = []
        for info in self.list_plugins():
            if info.status != STATUS_ENABLED:
                continue
            try:
                plugin = self.get_class(info.plugin_id)()
                urls = list(plugin.get_admin_urls())
            except Exception:
                continue
            if urls:
                pairs.append((info.plugin_id, urls))
        return pairs

    def set_settings(self, plugin_id: str, values: dict) -> dict:
        state = self._require_state(plugin_id)
        state.settings = {**(state.settings or {}), **values}
        state.save()
        return self.get_settings(plugin_id)

    def _audit(self, actor, action: str, plugin_id: str, before=None, after=None) -> None:
        from core.audit.service import audit

        audit(action, "plugin", plugin_id, actor=actor, before=before, after=after)

    def _require_record(self, plugin_id: str) -> PluginRecord:
        record = self.registry.get(plugin_id)
        if record is None:
            raise PluginNotFoundError(f"Plugin {plugin_id!r} is not discovered")
        return record

    def _require_state(self, plugin_id: str) -> PluginState:
        state = self._state(plugin_id)
        if state is None:
            raise PluginNotInstalledError(f"Plugin {plugin_id!r} is not installed")
        return state

    def _state(self, plugin_id: str) -> PluginState | None:
        return PluginState.objects.filter(plugin_id=plugin_id).first()

    def _manifest_of(self, plugin_id: str) -> PluginManifest | None:
        record = self.registry.get(plugin_id)
        return record.manifest if record else None

    def _register_runtime(self, plugin_id: str, plugin) -> None:
        registrations = self._event_registrations.setdefault(plugin_id, [])
        for event_type, handlers in plugin.get_event_handlers().items():
            handler_list = handlers if isinstance(handlers, (list, tuple)) else [handlers]
            for handler in handler_list:
                self.event_dispatcher.subscribe(event_type, handler)
                registrations.append((event_type, handler))

        service_keys = self._service_keys.setdefault(plugin_id, [])
        for key, factory in plugin.get_services().items():
            self.services.register(key, factory)
            service_keys.append(key)

        permissions = list(plugin.get_permissions())
        if permissions:
            self.permissions.register(plugin_id, permissions)
            self._permission_plugins.add(plugin_id)

        try:
            plugin.configure(self.get_settings(plugin_id))
        except Exception:
            plugin.configure({})

        gateway_codes = self._gateway_codes.setdefault(plugin_id, [])
        for gateway in plugin.get_payment_gateways():
            from core.payments.registry import payment_gateway_registry

            payment_gateway_registry.register(gateway)
            gateway_codes.append(gateway.code)

        provider_codes = self._shipping_provider_codes.setdefault(plugin_id, [])
        for provider in plugin.get_shipping_providers():
            from core.shipping.registry import shipping_provider_registry

            shipping_provider_registry.register(provider)
            provider_codes.append(provider.code)

        notification_codes = self._notification_provider_codes.setdefault(plugin_id, [])
        for provider in plugin.get_notification_providers():
            from core.notifications.registry import notification_provider_registry

            notification_provider_registry.register(provider)
            notification_codes.append(provider.code)

    def _unregister_runtime(self, plugin_id: str) -> None:
        for event_type, handler in self._event_registrations.pop(plugin_id, []):
            self.event_dispatcher.unsubscribe(event_type, handler)
        for key in self._service_keys.pop(plugin_id, []):
            self.services.unregister(key)
        if plugin_id in self._permission_plugins:
            self.permissions.unregister(plugin_id)
            self._permission_plugins.discard(plugin_id)

        for code in self._gateway_codes.pop(plugin_id, []):
            from core.payments.registry import payment_gateway_registry

            payment_gateway_registry.unregister(code)
        for code in self._shipping_provider_codes.pop(plugin_id, []):
            from core.shipping.registry import shipping_provider_registry

            shipping_provider_registry.unregister(code)

        for code in self._notification_provider_codes.pop(plugin_id, []):
            from core.notifications.registry import notification_provider_registry

            notification_provider_registry.unregister(code)


def core_version() -> str:
    from core import __version__

    return __version__
