from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.db.models import Q
from django.utils import timezone

from apps.catalog.models import Product
from core.exceptions import NotFoundError, ValidationError
from plugins.flash_sale.models import FlashSaleProduct

HUNDRED = Decimal("100")


def active_sales(product: Product | None = None, now=None) -> "list[FlashSaleProduct]":
    now = now or timezone.now()
    queryset = FlashSaleProduct.objects.filter(
        is_active=True, start_at__lte=now
    ).filter(Q(end_at__gte=now))
    if product is not None:
        queryset = queryset.filter(product=product)
    sales = list(queryset.order_by("end_at"))
    remaining = [sale for sale in sales if sale.remaining_quantity() != 0]
    return remaining


def apply_flash_sale_price(product, variant, price, context) -> Decimal | None:
    """Price modifier: reduce the price during an active flash sale."""
    if price is None:
        return None
    sales = active_sales(product)
    if not sales:
        return None

    price = Decimal(price)
    best = max(sales, key=lambda sale: Decimal(str(sale.discount_percent)))
    discount = Decimal(str(best.discount_percent)) / HUNDRED * price
    new_price = price - discount
    if new_price < 0:
        return Decimal("0")
    return new_price


def create_flash_sale(
    product_id: int,
    *,
    discount_percent,
    start_at,
    end_at,
    quantity: int = 0,
    is_active: bool = True,
) -> FlashSaleProduct:
    return upsert_flash_sale(
        product_id=product_id,
        discount_percent=discount_percent,
        start_at=start_at,
        end_at=end_at,
        quantity=quantity,
        is_active=is_active,
    )


def update_flash_sale(sale: FlashSaleProduct, *, product_id: int, **kwargs) -> FlashSaleProduct:
    return upsert_flash_sale(sale=sale, product_id=product_id, **kwargs)


def upsert_flash_sale(
    *,
    sale: FlashSaleProduct | None = None,
    product_id: int,
    discount_percent,
    start_at,
    end_at,
    quantity: int = 0,
    is_active: bool = True,
) -> FlashSaleProduct:
    product = Product.objects.filter(pk=product_id).first()
    if product is None:
        raise NotFoundError(f"Product {product_id} not found", code="flash_sale.product_not_found")

    try:
        percent = Decimal(str(discount_percent))
    except (InvalidOperation, TypeError):
        raise ValidationError("Discount percent must be a number", code="flash_sale.percent_invalid") from None
    if not (Decimal("0") <= percent <= HUNDRED):
        raise ValidationError("Discount percent must be between 0 and 100", code="flash_sale.percent_range")
    if end_at <= start_at:
        raise ValidationError("End date must be after start date", code="flash_sale.window_invalid")
    if quantity < 0:
        raise ValidationError("Quantity cannot be negative", code="flash_sale.quantity_invalid")

    fields = {
        "product": product,
        "discount_percent": percent,
        "start_at": start_at,
        "end_at": end_at,
        "quantity": quantity,
        "is_active": is_active,
    }
    if sale is None:
        return FlashSaleProduct.objects.create(**fields)
    for field, value in fields.items():
        setattr(sale, field, value)
    sale.save()
    return sale


def upcoming_window(days: int = 7) -> tuple:
    now = timezone.now()
    return now, now + timedelta(days=days)
