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


RTL_LANGUAGE_CODES = {"fa", "ar", "he", "ur", "ps", "ckb"}


class Language(BaseModel):
    """Site language defined in the admin (Languages section)."""

    name = models.CharField(max_length=100)
    code = models.CharField(max_length=10, unique=True)
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)
    direction = models.CharField(
        max_length=3, choices=[("ltr", "LTR"), ("rtl", "RTL")], default="ltr"
    )
    flag = models.CharField(max_length=10, blank=True)
    ordering = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Language"
        verbose_name_plural = "Languages"
        ordering = ["ordering", "code"]

    def __str__(self):
        return f"{self.name} ({self.code})"

    def save(self, *args, **kwargs):
        base_code = self.code.split("-")[0].lower()
        if self.direction not in ("ltr", "rtl"):
            self.direction = "ltr"
        if base_code in RTL_LANGUAGE_CODES:
            self.direction = "rtl"
        if self.is_default:
            Language.objects.exclude(pk=self.pk).update(is_default=False)
            self.is_active = True
        super().save(*args, **kwargs)


class LocaleStringResource(BaseModel):
    """One translated string of a language's word collection (catalog).

    `key` is the source string (English). Missing or empty values fall back
    to the source string.
    """

    language = models.ForeignKey(Language, on_delete=models.CASCADE, related_name="resources")
    key = models.CharField(max_length=255, db_index=True)
    value = models.TextField(blank=True)

    class Meta:
        verbose_name = "Translation"
        verbose_name_plural = "Translations"
        unique_together = [("language", "key")]
        ordering = ["language__code", "key"]

    def __str__(self):
        return f"{self.language.code}: {self.key[:50]}"


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
