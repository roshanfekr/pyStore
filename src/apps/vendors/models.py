from django.conf import settings
from django.db import models

from core.models import BaseModel, TimeStampedModel


class Vendor(BaseModel):
    STATUS_PENDING = "pending"
    STATUS_ACTIVE = "active"
    STATUS_DISABLED = "disabled"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_ACTIVE, "Active"),
        (STATUS_DISABLED, "Disabled"),
    ]
    ALLOWED_TRANSITIONS = {
        STATUS_PENDING: {STATUS_ACTIVE, STATUS_DISABLED},
        STATUS_ACTIVE: {STATUS_DISABLED},
        STATUS_DISABLED: {STATUS_ACTIVE},
    }

    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    email = models.EmailField(blank=True)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_PENDING)
    store = models.ForeignKey("stores.Store", related_name="vendors", on_delete=models.PROTECT)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name="owned_vendors", on_delete=models.PROTECT
    )
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = "Vendor"
        verbose_name_plural = "Vendors"
        ordering = ["name"]

    def __str__(self):
        return self.name


class VendorUser(TimeStampedModel):
    vendor = models.ForeignKey(Vendor, related_name="memberships", on_delete=models.CASCADE)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name="vendor_memberships", on_delete=models.CASCADE
    )
    is_admin = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Vendor user"
        verbose_name_plural = "Vendor users"
        constraints = [
            models.UniqueConstraint(fields=["vendor", "user"], name="uniq_vendor_user"),
        ]

    def __str__(self):
        return f"{self.vendor_id}:{self.user_id}"
