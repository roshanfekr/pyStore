from apps.catalog.services import resolve_price
from plugins.flash_sale.models import FlashSaleProduct


def sale_rows(sales: list[FlashSaleProduct]) -> list[dict]:
    rows = []
    for sale in sales:
        price = resolve_price(sale.product)
        rows.append(
            {
                "sale": sale,
                "product": sale.product,
                "sale_price": price,
                "original_price": sale.product.price,
                "discount_percent": sale.discount_percent,
                "remaining": sale.remaining_quantity(),
            }
        )
    return rows
