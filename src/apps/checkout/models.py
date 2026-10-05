from django.db import models

from core.models import BaseModel


class ShippingMethod(BaseModel):
    store = models.ForeignKey(
        "stores.Store", related_name="shipping_methods", on_delete=models.CASCADE
    )
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=50)
    provider_code = models.CharField(max_length=100, blank=True)
    flat_price = models.DecimalField(max_digits=18, decimal_places=4, default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Shipping method"
        verbose_name_plural = "Shipping methods"
        constraints = [
            models.UniqueConstraint(fields=["store", "code"], name="uniq_shipping_method_code"),
        ]

    def __str__(self):
        return f"{self.name} ({self.code})"


class PaymentMethod(BaseModel):
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=50, unique=True)
    description = models.CharField(max_length=300, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Payment method"
        verbose_name_plural = "Payment methods"

    def __str__(self):
        return f"{self.name} ({self.code})"


def ensure_default_payment_methods() -> None:
    from django.db import transaction

    with transaction.atomic():
        PaymentMethod.objects.get_or_create(
            code="cash_on_delivery",
            defaults={"name": "Cash on delivery", "description": "Pay when the order arrives"},
        )
        PaymentMethod.objects.get_or_create(
            code="bank_transfer",
            defaults={"name": "Bank transfer", "description": "Pay via bank transfer"},
        )
