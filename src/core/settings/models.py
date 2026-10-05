from django.db import models


class Setting(models.Model):
    namespace = models.CharField(max_length=100, default="global", db_index=True)
    key = models.CharField(max_length=200)
    value = models.JSONField(null=True, blank=True)
    is_sensitive = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Setting"
        verbose_name_plural = "Settings"
        constraints = [
            models.UniqueConstraint(fields=["namespace", "key"], name="uniq_setting_ns_key"),
        ]

    def __str__(self):
        return f"{self.namespace}:{self.key}"
