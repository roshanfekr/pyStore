from dataclasses import dataclass
from decimal import Decimal

from apps.pricing.discounts import apply_discount, validate_discount
from apps.pricing.engine import resolve_product_price


@dataclass(frozen=True)
class CartLineCalculation:
    item_id: str
    product_name: str
    quantity: int
    unit_price: Decimal
    line_total: Decimal


@dataclass(frozen=True)
class CartCalculation:
    lines: tuple[CartLineCalculation, ...]
    subtotal: Decimal
    discount_amount: Decimal
    total: Decimal
    coupon_code: str | None = None


def calculate_cart(cart, *, customer=None) -> CartCalculation:
    lines: list[CartLineCalculation] = []
    subtotal = Decimal("0.0000")

    for item in cart.items.select_related("product", "variant", "product__store").order_by("created_at"):
        unit_price = resolve_product_price(
            item.product,
            item.variant,
            customer=customer,
            store=cart.store,
            quantity=item.quantity,
        )
        line_total = (unit_price * item.quantity).quantize(Decimal("0.0001"))
        lines.append(
            CartLineCalculation(
                item_id=str(item.id),
                product_name=item.product.name,
                quantity=item.quantity,
                unit_price=unit_price,
                line_total=line_total,
            )
        )
        subtotal += line_total

    discount_amount = Decimal("0.0000")
    coupon_code = None
    if cart.coupon_id:
        discount = cart.coupon
        validate_discount(discount, amount=subtotal, customer=customer)
        application = apply_discount(discount, subtotal, customer=customer)
        discount_amount = application.amount
        coupon_code = discount.coupon_code

    return CartCalculation(
        lines=tuple(lines),
        subtotal=subtotal,
        discount_amount=discount_amount,
        total=subtotal - discount_amount,
        coupon_code=coupon_code,
    )
