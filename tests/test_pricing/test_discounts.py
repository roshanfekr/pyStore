from datetime import timedelta
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.catalog.services import create_product
from apps.pricing.discounts import (
    apply_discount,
    calculate_discount,
    get_discount_by_coupon,
    record_usage,
    register_discount_type,
    validate_discount,
)
from apps.pricing.models import Discount, DiscountUsage
from apps.stores.services import create_store

User = get_user_model()

pytestmark = [pytest.mark.django_db]

AMOUNT = Decimal("200.0000")


@pytest.fixture
def store(db):
    return create_store("Discount Store")


@pytest.fixture
def customer(db):
    return User.objects.create_user(email="buyer@example.com", password="Str0ng!Passw0rd")


def _discount(**kwargs) -> Discount:
    defaults = dict(name="Test Discount", discount_type="percentage", value=Decimal("10"))
    defaults.update(kwargs)
    return Discount.objects.create(**defaults)


def test_percentage_discount():
    discount = _discount(value=Decimal("15"))
    result = apply_discount(discount, AMOUNT)
    assert result.amount == Decimal("30.0000")
    assert result.discounted_total == Decimal("170.0000")


def test_fixed_amount_discount():
    discount = _discount(discount_type="fixed_amount", value=Decimal("50"))
    result = apply_discount(discount, AMOUNT)
    assert result.amount == Decimal("50.0000")


def test_fixed_amount_capped_at_order_total():
    discount = _discount(discount_type="fixed_amount", value=Decimal("500"))
    assert calculate_discount(discount, AMOUNT) == AMOUNT


def test_percentage_capped_by_max_discount():
    discount = _discount(value=Decimal("50"), max_discount_amount=Decimal("20"))
    assert calculate_discount(discount, AMOUNT) == Decimal("20.0000")


def test_min_order_amount_condition():
    discount = _discount(min_order_amount=Decimal("300"))
    with pytest.raises(Exception, match="Minimum"):
        validate_discount(discount, amount=AMOUNT)
    validate_discount(discount, amount=Decimal("400.0000"))


def test_start_end_date_window():
    now = timezone.now()
    discount = _discount(start_at=now + timedelta(hours=1))
    with pytest.raises(Exception, match="not started"):
        validate_discount(discount, at=now)

    expired = _discount(end_at=now - timedelta(hours=1))
    with pytest.raises(Exception, match="expired"):
        validate_discount(expired, at=now)


def test_inactive_discount_rejected():
    discount = _discount(is_active=False)
    with pytest.raises(Exception, match="not active"):
        validate_discount(discount)


def test_usage_limit_total():
    discount = _discount(usage_limit=1)
    record_usage(discount)
    with pytest.raises(Exception, match="usage limit"):
        validate_discount(discount)


def test_usage_limit_per_customer(store, customer):
    discount = _discount(usage_limit_per_customer=1)
    record_usage(discount, user=customer)

    with pytest.raises(Exception, match="already used"):
        validate_discount(discount, customer=customer)

    other = User.objects.create_user(email="other@example.com", password="Str0ng!Passw0rd")
    validate_discount(discount, customer=other)


def test_customer_restricted_discount(store, customer):
    discount = _discount()
    discount.customers.add(customer)

    with pytest.raises(Exception, match="customer"):
        validate_discount(discount, customer=None)
    with pytest.raises(Exception, match="not available"):
        stranger = User.objects.create_user(email="s@example.com", password="Str0ng!Passw0rd")
        validate_discount(discount, customer=stranger)
    validate_discount(discount, customer=customer)


def test_product_scope_validation(store):
    product_a = create_product(store, "Scoped A", price=Decimal("10.0000"))
    product_b = create_product(store, "Scoped B", price=Decimal("10.0000"))

    discount = _discount(scope="product", product=product_a)
    validate_discount(discount, product=product_a)
    with pytest.raises(Exception, match="does not apply"):
        validate_discount(discount, product=product_b)


def test_category_scope_validation(store):
    from apps.catalog.models import Category

    parent = Category.objects.create(name="Cat Parent", slug="cat-parent")
    child = Category.objects.create(name="Cat Child", slug="cat-child", parent=parent)
    in_category = create_product(store, "In Cat", price=Decimal("10.0000"), category=child)
    outside = create_product(store, "Outside Cat", price=Decimal("10.0000"))

    discount = _discount(scope="category", category=parent)
    validate_discount(discount, product=in_category)

    with pytest.raises(Exception, match="does not apply"):
        validate_discount(discount, product=outside)


def test_coupon_code_lookup_and_case_insensitivity():
    _discount(name="Coupon Deal", coupon_code="save20")
    found = get_discount_by_coupon(" SAVE20 ")
    assert found.name == "Coupon Deal"

    from core.exceptions import NotFoundError

    with pytest.raises(NotFoundError):
        get_discount_by_coupon("NOPE")


def test_record_usage_tracking(store, customer):
    discount = _discount()
    record_usage(discount, user=customer, reference="ORDER-1")
    record_usage(discount, user=customer, reference="ORDER-2")

    discount.refresh_from_db()
    assert discount.used_count == 2
    assert DiscountUsage.objects.filter(discount=discount).count() == 2


def test_custom_discount_type_plugin_friendly():
    def double_calculator(discount, amount):
        return min(amount * 2, amount)

    register_discount_type("double", double_calculator)
    discount = _discount(discount_type="double", value=Decimal("10"))
    assert calculate_discount(discount, AMOUNT) == AMOUNT

    from apps.pricing.discounts import DISCOUNT_TYPE_CALCULATORS

    del DISCOUNT_TYPE_CALCULATORS["double"]


def test_soft_deleted_discount_rejected():
    discount = _discount()
    discount.delete()
    with pytest.raises(Exception, match="not active"):
        validate_discount(discount)
