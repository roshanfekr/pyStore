from django.conf import settings
from django.db import models

from core.models import BaseModel


class PriceList(BaseModel):
    name = models.CharField(max_length=200)
    store = models.ForeignKey(
        "stores.Store", null=True, blank=True, related_name="price_lists", on_delete=models.CASCADE
    )
    role = models.ForeignKey(
        "identity.Role", null=True, blank=True, related_name="price_lists", on_delete=models.CASCADE
    )
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, related_name="price_lists",
        on_delete=models.CASCADE,
    )
    priority = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Price list"
        verbose_name_plural = "Price lists"
        ordering = ["-priority", "name"]

    def __str__(self):
        return self.name


class PriceListEntry(models.Model):
    price_list = models.ForeignKey(PriceList, related_name="entries", on_delete=models.CASCADE)
    product = models.ForeignKey(
        "catalog.Product", null=True, blank=True, related_name="price_entries", on_delete=models.CASCADE
    )
    variant = models.ForeignKey(
        "catalog.ProductVariant", null=True, blank=True, related_name="price_entries",
        on_delete=models.CASCADE,
    )
    price = models.DecimalField(max_digits=18, decimal_places=4)
    min_quantity = models.PositiveIntegerField(default=1)
    max_quantity = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        verbose_name = "Price list entry"
        verbose_name_plural = "Price list entries"
        ordering = ["min_quantity"]


class ScheduledPrice(models.Model):
    product = models.ForeignKey(
        "catalog.Product", null=True, blank=True, related_name="scheduled_prices", on_delete=models.CASCADE
    )
    variant = models.ForeignKey(
        "catalog.ProductVariant", null=True, blank=True, related_name="scheduled_prices",
        on_delete=models.CASCADE,
    )
    price = models.DecimalField(max_digits=18, decimal_places=4)
    start_at = models.DateTimeField(null=True, blank=True)
    end_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Scheduled price"
        verbose_name_plural = "Scheduled prices"
        ordering = ["-start_at"]


class Discount(BaseModel):
    TYPE_PERCENTAGE = "percentage"
    TYPE_FIXED_AMOUNT = "fixed_amount"
    TYPE_CHOICES = [
        (TYPE_PERCENTAGE, "Percentage"),
        (TYPE_FIXED_AMOUNT, "Fixed amount"),
    ]

    SCOPE_PRODUCT = "product"
    SCOPE_CATEGORY = "category"
    SCOPE_CART = "cart"
    SCOPE_CHOICES = [
        (SCOPE_PRODUCT, "Product"),
        (SCOPE_CATEGORY, "Category"),
        (SCOPE_CART, "Cart"),
    ]

    name = models.CharField(max_length=200)
    coupon_code = models.CharField(max_length=50, unique=True, null=True, blank=True)
    discount_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default=TYPE_PERCENTAGE)
    value = models.DecimalField(max_digits=18, decimal_places=4)
    scope = models.CharField(max_length=20, choices=SCOPE_CHOICES, default=SCOPE_CART)
    product = models.ForeignKey(
        "catalog.Product", null=True, blank=True, related_name="discounts", on_delete=models.CASCADE
    )
    category = models.ForeignKey(
        "catalog.Category", null=True, blank=True, related_name="discounts", on_delete=models.CASCADE
    )
    customers = models.ManyToManyField(
        settings.AUTH_USER_MODEL, related_name="discounts", blank=True
    )
    min_order_amount = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    max_discount_amount = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    start_at = models.DateTimeField(null=True, blank=True)
    end_at = models.DateTimeField(null=True, blank=True)
    usage_limit = models.PositiveIntegerField(null=True, blank=True)
    usage_limit_per_customer = models.PositiveIntegerField(null=True, blank=True)
    used_count = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Discount"
        verbose_name_plural = "Discounts"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.coupon_code:
            self.coupon_code = self.coupon_code.strip().upper()
        super().save(*args, **kwargs)


class DiscountUsage(models.Model):
    discount = models.ForeignKey(Discount, related_name="usages", on_delete=models.CASCADE)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, related_name="discount_usages",
        on_delete=models.SET_NULL,
    )
    reference = models.CharField(max_length=200, blank=True)
    used_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Discount usage"
        verbose_name_plural = "Discount usages"


class TaxClass(BaseModel):
    name = models.CharField(max_length=100, unique=True)
    is_default = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Tax class"
        verbose_name_plural = "Tax classes"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.is_default:
            TaxClass.objects.exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)


class TaxRate(models.Model):
    tax_class = models.ForeignKey(TaxClass, related_name="rates", on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    rate = models.DecimalField(max_digits=8, decimal_places=4)
    country = models.CharField(max_length=2, blank=True)
    state = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Tax rate"
        verbose_name_plural = "Tax rates"

    def __str__(self):
        return f"{self.name} ({self.rate}%)"


class CustomerTaxInfo(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, related_name="tax_info", on_delete=models.CASCADE
    )
    tax_exempt = models.BooleanField(default=False)
    tax_id = models.CharField(max_length=50, blank=True)


class ProductTaxSetting(models.Model):
    product = models.OneToOneField(
        "catalog.Product", related_name="tax_setting", on_delete=models.CASCADE
    )
    tax_class = models.ForeignKey(TaxClass, related_name="product_settings", on_delete=models.CASCADE)
