from core.exceptions import ApplicationError


class PluginError(ApplicationError):
    message = "Plugin error"
    code = "plugin_error"


class PluginManifestError(PluginError):
    message = "Invalid plugin manifest"
    code = "plugin_manifest_error"


class PluginNotFoundError(PluginError):
    message = "Plugin not found"
    code = "plugin_not_found"
    status_code = 404


class PluginNotInstalledError(PluginError):
    message = "Plugin is not installed"
    code = "plugin_not_installed"
    status_code = 404


class PluginAlreadyInstalledError(PluginError):
    message = "Plugin is already installed"
    code = "plugin_already_installed"
    status_code = 409


class PluginDependencyError(PluginError):
    message = "Plugin dependency error"
    code = "plugin_dependency_error"
    status_code = 409


class PluginVersionError(PluginError):
    message = "Plugin version error"
    code = "plugin_version_error"
