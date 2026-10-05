import hashlib
import importlib.util
import sys
from pathlib import Path

from core.plugins.exceptions import PluginManifestError
from core.plugins.manifest import PluginRecord

SRC_DIR = Path(__file__).resolve().parents[2]


def load_entry_class(record: PluginRecord) -> type:
    module_name, _, class_name = record.manifest.entry_point.partition(":")
    if not module_name or not class_name:
        raise PluginManifestError(
            f"Invalid entry_point {record.manifest.entry_point!r} (expected 'module:Class')"
        )

    module_file = record.path / f"{module_name}.py"
    if not module_file.exists():
        raise PluginManifestError(f"Entry module not found: {module_file}")

    try:
        path_token = hashlib.sha1(
            f"{record.path}|{module_file.stat().st_mtime_ns}".encode()
        ).hexdigest()[:8]
    except OSError:
        path_token = hashlib.sha1(str(record.path).encode()).hexdigest()[:8]
    unique_name = f"pystore_plugin_{record.manifest.plugin_id}_{module_name}_{path_token}"
    if unique_name in sys.modules:
        module = sys.modules[unique_name]
    else:
        spec = importlib.util.spec_from_file_location(unique_name, module_file)
        if spec is None or spec.loader is None:
            raise PluginManifestError(f"Cannot load plugin module: {module_file}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[unique_name] = module
        try:
            spec.loader.exec_module(module)
        except Exception as exc:
            raise PluginManifestError(f"Failed to load plugin module {module_file}: {exc}") from exc

    entry_class = getattr(module, class_name, None)
    if entry_class is None:
        raise PluginManifestError(f"Entry class {class_name!r} not found in {module_file}")
    return entry_class


def get_discovered_plugin_apps() -> list[str]:
    plugins_dir = SRC_DIR / "plugins"
    if not plugins_dir.exists():
        return []
    return sorted(
        f"plugins.{entry.name}"
        for entry in plugins_dir.iterdir()
        if entry.is_dir() and (entry / "plugin.json").exists()
    )
