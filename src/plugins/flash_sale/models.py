from django.db import models

from apps.catalog.models import Product
from core.models import BaseModel


class FlashSaleProduct(BaseModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="flash_sales")
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2)
    start_at = models.DateTimeField()
    end_at = models.DateTimeField()
    quantity = models.PositiveIntegerField(default=0, help_text="Maximum units sold at the sale price. 0 = unlimited.")
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Flash sale"
        verbose_name_plural = "Flash sales"
        ordering = ["-start_at"]

    def __str__(self):
        return f"{self.product.name} -{self.discount_percent}%"

    def remaining_quantity(self) -> int:
        if self.quantity == 0:
            return -1
        from apps.orders.models import OrderItem

        claimed = OrderItem.objects.filter(
            product=self.product,
            order__created_at__gte=self.start_at,
            order__created_at__lte=self.end_at,
        ).aggregate(total=models.Sum("quantity"))["total"] or 0
        return max(self.quantity - claimed, 0)
