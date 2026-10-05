from dataclasses import dataclass, field
from decimal import Decimal

from apps.cart.models import Cart


@dataclass
class CheckoutLine:
    cart_item_id: str
    product: object
    variant: object | None
    name: str
    sku: str
    quantity: int
    unit_price: Decimal
    line_total: Decimal
    price_changed: bool = False


@dataclass
class CheckoutContext:
    cart: Cart
    user: object | None = None
    email: str = ""
    shipping_address: dict = field(default_factory=dict)
    shipping_method_code: str = ""
    payment_method_code: str = ""

    lines: list = field(default_factory=list)
    subtotal: Decimal = Decimal("0.0000")
    discount_amount: Decimal = Decimal("0.0000")
    shipping_amount: Decimal = Decimal("0.0000")
    tax_amount: Decimal = Decimal("0.0000")
    total: Decimal = Decimal("0.0000")
    coupon_code: str | None = None
    order: object | None = None
