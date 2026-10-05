from django.conf import settings
from django.db import models
from django.db.models import Q

from core.models import BaseModel, TimeStampedModel


class Warehouse(BaseModel):
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=50, unique=True)
    store = models.ForeignKey("stores.Store", related_name="warehouses", on_delete=models.PROTECT)
    address_line = models.CharField(max_length=300, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=30, blank=True)
    country = models.CharField(max_length=2, blank=True)
    is_default = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Warehouse"
        verbose_name_plural = "Warehouses"
        ordering = ["code"]

    def __str__(self):
        return f"{self.name} ({self.code})"


class WarehouseLocation(models.Model):
    warehouse = models.ForeignKey(Warehouse, related_name="locations", on_delete=models.CASCADE)
    code = models.CharField(max_length=50)
    description = models.CharField(max_length=300, blank=True)

    class Meta:
        verbose_name = "Warehouse location"
        verbose_name_plural = "Warehouse locations"
        constraints = [
            models.UniqueConstraint(fields=["warehouse", "code"], name="uniq_warehouse_location"),
        ]

    def __str__(self):
        return f"{self.warehouse.code}:{self.code}"


class InventoryItem(BaseModel):
    warehouse = models.ForeignKey(Warehouse, related_name="inventory_items", on_delete=models.PROTECT)
    product = models.ForeignKey(
        "catalog.Product", null=True, blank=True, related_name="inventory_items", on_delete=models.CASCADE
    )
    variant = models.ForeignKey(
        "catalog.ProductVariant", null=True, blank=True, related_name="inventory_items", on_delete=models.CASCADE
    )
    location = models.ForeignKey(
        WarehouseLocation, null=True, blank=True, related_name="inventory_items", on_delete=models.SET_NULL
    )
    stock_quantity = models.PositiveIntegerField(default=0)
    reserved_quantity = models.PositiveIntegerField(default=0)
    low_stock_threshold = models.PositiveIntegerField(default=5)
    backorder_allowed = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Inventory item"
        verbose_name_plural = "Inventory items"
        constraints = [
            models.UniqueConstraint(
                fields=["warehouse", "product"], condition=Q(product__isnull=False),
                name="uniq_inventory_warehouse_product",
            ),
            models.UniqueConstraint(
                fields=["warehouse", "variant"], condition=Q(variant__isnull=False),
                name="uniq_inventory_warehouse_variant",
            ),
            models.CheckConstraint(
                condition=Q(product__isnull=False, variant__isnull=True)
                | Q(product__isnull=True, variant__isnull=False),
                name="inventory_target_xor",
            ),
        ]

    def __str__(self):
        target = self.variant.sku if self.variant_id else (self.product.name if self.product else "?")
        return f"{self.warehouse.code}:{target}"

    @property
    def available_quantity(self) -> int:
        return self.stock_quantity - self.reserved_quantity

    @property
    def is_backordered(self) -> bool:
        return self.reserved_quantity > self.stock_quantity

    @property
    def stock_status(self) -> str:
        if self.available_quantity <= 0:
            return "out_of_stock"
        if self.available_quantity <= self.low_stock_threshold:
            return "low_stock"
        return "in_stock"


class InventoryTransaction(TimeStampedModel):
    TYPE_RECEIVE = "receive"
    TYPE_SHIP = "ship"
    TYPE_RESERVE = "reserve"
    TYPE_RELEASE = "release"
    TYPE_ADJUST = "adjust"
    TYPE_TRANSFER_OUT = "transfer_out"
    TYPE_TRANSFER_IN = "transfer_in"
    TYPE_CHOICES = [
        (TYPE_RECEIVE, "Receive"),
        (TYPE_SHIP, "Ship"),
        (TYPE_RESERVE, "Reserve"),
        (TYPE_RELEASE, "Release"),
        (TYPE_ADJUST, "Adjust"),
        (TYPE_TRANSFER_OUT, "Transfer out"),
        (TYPE_TRANSFER_IN, "Transfer in"),
    ]

    inventory_item = models.ForeignKey(
        InventoryItem, related_name="transactions", on_delete=models.PROTECT
    )
    transaction_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    stock_delta = models.IntegerField(default=0)
    reserved_delta = models.IntegerField(default=0)
    resulting_stock = models.PositiveIntegerField()
    resulting_reserved = models.PositiveIntegerField()
    reference = models.CharField(max_length=200, blank=True)
    note = models.CharField(max_length=500, blank=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, related_name="inventory_transactions",
        on_delete=models.SET_NULL,
    )

    class Meta:
        verbose_name = "Inventory transaction"
        verbose_name_plural = "Inventory transactions"
        ordering = ["-created_at"]
