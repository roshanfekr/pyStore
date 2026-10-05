from dataclasses import dataclass
from decimal import Decimal

from django.utils import timezone

from apps.pricing.models import Discount, DiscountUsage
from core.exceptions import ConflictError, NotFoundError, ValidationError

DISCOUNT_TYPE_CALCULATORS: dict = {}


def register_discount_type(name: str, calculator) -> None:
    """Plugin-friendly extension point: custom discount type calculators."""

    DISCOUNT_TYPE_CALCULATORS[name] = calculator


def _percentage_calculator(discount: Discount, amount: Decimal) -> Decimal:
    calculated = (amount * discount.value / Decimal("100")).quantize(Decimal("0.0001"))
    if discount.max_discount_amount is not None:
        calculated = min(calculated, discount.max_discount_amount)
    return calculated


def _fixed_amount_calculator(discount: Discount, amount: Decimal) -> Decimal:
    return min(discount.value, amount)


register_discount_type("percentage", _percentage_calculator)
register_discount_type("fixed_amount", _fixed_amount_calculator)


@dataclass(frozen=True)
class DiscountApplication:
    discount_id: str
    name: str
    amount: Decimal
    discounted_total: Decimal


def _validate_window(discount: Discount, at) -> None:
    if discount.start_at is not None and at < discount.start_at:
        raise ValidationError("Discount has not started yet", code="discounts.not_started")
    if discount.end_at is not None and at > discount.end_at:
        raise ValidationError("Discount has expired", code="discounts.expired")


def _validate_usage_limits(discount: Discount, customer) -> None:
    if discount.usage_limit is not None and discount.used_count >= discount.usage_limit:
        raise ConflictError("Discount usage limit reached", code="discounts.usage_limit")

    if discount.usage_limit_per_customer is not None:
        if customer is None or not getattr(customer, "is_authenticated", False):
            return
        used = DiscountUsage.objects.filter(discount=discount, user=customer).count()
        if used >= discount.usage_limit_per_customer:
            raise ConflictError(
                "Customer has already used this discount", code="discounts.customer_limit"
            )


def _validate_customers(discount: Discount, customer) -> None:
    if not discount.customers.exists():
        return
    if customer is None or not getattr(customer, "is_authenticated", False):
        raise ValidationError("Discount is customer-restricted", code="discounts.customer_required")
    if not discount.customers.filter(pk=customer.pk).exists():
        raise ValidationError("Discount not available for this customer", code="discounts.customer_denied")


def validate_discount(
    discount: Discount,
    *,
    amount: Decimal | None = None,
    customer=None,
    product=None,
    category=None,
    at=None,
) -> None:
    at = at or timezone.now()

    if not discount.is_active or discount.is_deleted:
        raise ValidationError("Discount is not active", code="discounts.inactive")

    _validate_window(discount, at)
    _validate_customers(discount, customer)

    if amount is not None and discount.min_order_amount is not None:
        if amount < discount.min_order_amount:
            raise ValidationError(
                f"Minimum order amount is {discount.min_order_amount}",
                code="discounts.min_order",
            )

    if discount.scope == "product" and product is not None and discount.product_id:
        if product.id != discount.product_id:
            raise ValidationError("Discount does not apply to this product", code="discounts.not_applicable")
    if discount.scope == "category" and discount.category_id:
        product_category = product.category if product is not None else category
        category_ids = {discount.category_id, *discount.category.descendant_ids()}
        if product_category is None or product_category.id not in category_ids:
            raise ValidationError("Discount does not apply to this category", code="discounts.not_applicable")

    _validate_usage_limits(discount, customer)


def calculate_discount(discount: Discount, amount: Decimal) -> Decimal:
    calculator = DISCOUNT_TYPE_CALCULATORS.get(discount.discount_type)
    if calculator is None:
        raise ValidationError(
            f"Unknown discount type {discount.discount_type!r}", code="discounts.unknown_type"
        )
    calculated = calculator(discount, amount)
    return min(calculated, amount).quantize(Decimal("0.0001"))


def apply_discount(
    discount: Discount,
    amount: Decimal,
    *,
    customer=None,
    product=None,
    category=None,
) -> DiscountApplication:
    validate_discount(
        discount, amount=amount, customer=customer, product=product, category=category
    )
    calculated = calculate_discount(discount, amount)
    return DiscountApplication(
        discount_id=str(discount.id),
        name=discount.name,
        amount=calculated,
        discounted_total=amount - calculated,
    )


def record_usage(discount: Discount, user=None, reference: str = "") -> None:
    DiscountUsage.objects.create(discount=discount, user=user, reference=reference)
    discount.used_count = discount.used_count + 1
    discount.save(update_fields=["used_count"])


def get_discount_by_coupon(code: str) -> Discount:
    discount = Discount.objects.filter(
        coupon_code=(code or "").strip().upper(), scope="cart"
    ).first()
    if discount is None:
        raise NotFoundError("Invalid coupon code", code="discounts.invalid_coupon")
    return discount
