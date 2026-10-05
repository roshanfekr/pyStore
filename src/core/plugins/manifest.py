import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from packaging.version import InvalidVersion, Version

from core.plugins.exceptions import PluginManifestError

REQUIRED_KEYS = ("id", "name", "version", "entry_point")
PLUGIN_ID_REGEX = re.compile(r"^[a-z][a-z0-9_]*$")


@dataclass(frozen=True)
class PluginManifest:
    plugin_id: str
    name: str
    version: Version
    entry_point: str
    author: str = ""
    description: str = ""
    dependencies: tuple[str, ...] = field(default=())
    minimum_core_version: Version | None = None


@dataclass
class PluginRecord:
    manifest: PluginManifest
    path: Path

    @property
    def plugin_id(self) -> str:
        return self.manifest.plugin_id


def parse_manifest(data) -> PluginManifest:
    if not isinstance(data, dict):
        raise PluginManifestError("Manifest must be a JSON object")

    missing = [key for key in REQUIRED_KEYS if not data.get(key)]
    if missing:
        raise PluginManifestError(f"Missing required manifest fields: {', '.join(missing)}")

    plugin_id = data["id"]
    if not PLUGIN_ID_REGEX.match(plugin_id):
        raise PluginManifestError(f"Invalid plugin id: {plugin_id!r}")

    try:
        version = Version(str(data["version"]))
    except InvalidVersion:
        raise PluginManifestError(f"Invalid version: {data['version']!r}") from None

    minimum_core_version = None
    if data.get("minimum_core_version"):
        try:
            minimum_core_version = Version(str(data["minimum_core_version"]))
        except InvalidVersion:
            raise PluginManifestError(
                f"Invalid minimum_core_version: {data['minimum_core_version']!r}"
            ) from None

    dependencies = tuple(data.get("dependencies") or [])

    return PluginManifest(
        plugin_id=plugin_id,
        name=str(data["name"]),
        version=version,
        entry_point=str(data["entry_point"]),
        author=str(data.get("author") or ""),
        description=str(data.get("description") or ""),
        dependencies=dependencies,
        minimum_core_version=minimum_core_version,
    )


def load_manifest(path: Path) -> PluginManifest:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise PluginManifestError(f"Cannot read manifest {path}: {exc}") from None
    except json.JSONDecodeError as exc:
        raise PluginManifestError(f"Manifest {path} is not valid JSON: {exc}") from None
    return parse_manifest(data)
