from django.db import models

STATUS_INSTALLED = "installed"
STATUS_ENABLED = "enabled"
STATUS_DISABLED = "disabled"
STATUS_CHOICES = [
    (STATUS_INSTALLED, "Installed"),
    (STATUS_ENABLED, "Enabled"),
    (STATUS_DISABLED, "Disabled"),
]


class PluginState(models.Model):
    plugin_id = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=200)
    version = models.CharField(max_length=32)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_INSTALLED)
    settings = models.JSONField(default=dict, blank=True)
    installed_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Plugin state"
        verbose_name_plural = "Plugin states"

    def __str__(self):
        return f"{self.plugin_id} ({self.status})"
