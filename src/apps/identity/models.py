import uuid
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone

from core.models import BaseModel, TimeStampedModel
from core.validators import validate_phone

from .managers import UserManager


class User(AbstractBaseUser, PermissionsMixin):
    USER_TYPE_CUSTOMER = "customer"
    USER_TYPE_STAFF = "staff"
    USER_TYPE_CHOICES = [
        (USER_TYPE_CUSTOMER, "Customer"),
        (USER_TYPE_STAFF, "Staff"),
    ]

    id = models.BigAutoField(primary_key=True, auto_created=True, serialize=False, verbose_name="ID")
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    user_type = models.CharField(
        max_length=10, choices=USER_TYPE_CHOICES, default=USER_TYPE_CUSTOMER
    )
    email_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"

    def __str__(self):
        return self.email

    @property
    def is_customer(self) -> bool:
        return self.user_type == self.USER_TYPE_CUSTOMER

    @property
    def is_staff_user(self) -> bool:
        return self.user_type == self.USER_TYPE_STAFF


class Customer(BaseModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, related_name="customer_profile", on_delete=models.CASCADE
    )
    phone = models.CharField(max_length=16, blank=True, validators=[validate_phone])

    class Meta:
        verbose_name = "Customer"
        verbose_name_plural = "Customers"

    def __str__(self):
        return f"Customer {self.user_id}"


class Address(BaseModel):
    """A reusable, customer-owned saved address.

    This is the customer's address book entry. It is deliberately distinct
    from ``apps.orders.models.OrderAddress``, which is the immutable snapshot
    recorded on an order: changing or deleting a saved address must never
    change the address snapshot of an existing order.
    """

    customer = models.ForeignKey(
        Customer, related_name="addresses", on_delete=models.CASCADE
    )
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    email = models.CharField(max_length=254, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    country = models.CharField(max_length=2)
    state = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=30, blank=True)
    address_line = models.CharField(max_length=300)
    is_default = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Customer address"
        verbose_name_plural = "Customer addresses"
        ordering = ["-is_default", "id"]

    def __str__(self) -> str:
        label = f"{self.first_name} {self.last_name}".strip()
        return label or f"Address {self.pk}"

    def as_snapshot(self) -> dict:
        """Return the address fields copied into an order address snapshot."""
        return {
            "first_name": self.first_name,
            "last_name": self.last_name,
            "email": self.email,
            "phone": self.phone,
            "country": self.country,
            "state": self.state,
            "city": self.city,
            "postal_code": self.postal_code,
            "address_line": self.address_line,
        }


class Permission(TimeStampedModel):
    codename = models.CharField(max_length=100, unique=True)
    display_name = models.CharField(max_length=200, blank=True)
    source = models.CharField(max_length=100, default="core")

    class Meta:
        verbose_name = "Permission"
        verbose_name_plural = "Permissions"
        ordering = ["codename"]

    def __str__(self):
        return self.codename


class Role(TimeStampedModel):
    name = models.CharField(max_length=100, unique=True)
    description = models.CharField(max_length=255, blank=True)
    is_system = models.BooleanField(default=False)
    permissions = models.ManyToManyField("identity.Permission", related_name="roles", blank=True)
    users = models.ManyToManyField(
        settings.AUTH_USER_MODEL, related_name="roles", blank=True
    )

    class Meta:
        verbose_name = "Role"
        verbose_name_plural = "Roles"

    def __str__(self):
        return self.name


PASSWORD_RESET_TTL = timedelta(hours=1)
EMAIL_VERIFICATION_TTL = timedelta(hours=48)


class ExpirableTokenModel(models.Model):
    id = models.BigAutoField(primary_key=True, auto_created=True, serialize=False, verbose_name="ID")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True

    def is_valid(self) -> bool:
        return self.used_at is None and timezone.now() < self.expires_at


class PasswordResetToken(ExpirableTokenModel):
    class Meta:
        verbose_name = "Password reset token"
        verbose_name_plural = "Password reset tokens"


class EmailVerificationToken(ExpirableTokenModel):
    class Meta:
        verbose_name = "Email verification token"
        verbose_name_plural = "Email verification tokens"
