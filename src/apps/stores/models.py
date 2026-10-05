from django.db import models

from core.models import BaseModel


class Store(BaseModel):
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    default_language = models.CharField(max_length=10, default="en")
    supported_languages = models.JSONField(default=list, blank=True)
    default_currency = models.CharField(max_length=10, default="USD")
    supported_currencies = models.JSONField(default=list, blank=True)
    timezone = models.CharField(max_length=64, default="UTC")
    products_per_page = models.PositiveIntegerField(default=20)
    allow_guest_checkout = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Store"
        verbose_name_plural = "Stores"
        ordering = ["name"]

    def __str__(self):
        return self.name


class StoreDomain(models.Model):
    domain = models.CharField(max_length=253, unique=True)
    store = models.ForeignKey(Store, related_name="domains", on_delete=models.CASCADE)
    ssl_enabled = models.BooleanField(default=True)
    is_primary = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Store domain"
        verbose_name_plural = "Store domains"

    def __str__(self):
        return self.domain

    def save(self, *args, **kwargs):
        self.domain = self.domain.lower().strip()
        if self.is_primary:
            StoreDomain.objects.filter(store=self.store).exclude(pk=self.pk).update(
                is_primary=False
            )
        super().save(*args, **kwargs)
