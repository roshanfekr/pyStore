from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.cart.models import Cart
from apps.cart.services import (
    add_to_cart,
    attach_coupon,
    get_or_create_cart,
)
from apps.catalog.services import add_variant, create_product, publish_product, update_product
from apps.checkout.models import PaymentMethod, ShippingMethod
from apps.checkout.pipeline import CheckoutPipeline
from apps.checkout.services import execute_checkout
from apps.inventory.services import create_warehouse, get_or_create_inventory, receive_stock
from apps.orders.models import Order, OrderAddress, OrderItem
from apps.pricing.models import Discount
from apps.stores.services import create_store
from core.exceptions import ConflictError, NotFoundError, ValidationError

User = get_user_model()

pytestmark = [pytest.mark.django_db]

PRICE = Decimal("100.0000")

ADDRESS = {
    "first_name": "Ali",
    "last_name": "Rezaei",
    "country": "IR",
    "state": "TEH",
    "city": "Tehran",
    "postal_code": "12345",
    "address_line": "Street 1, No 2",
    "phone": "+989121234567",
}


@pytest.fixture
def store(db):
    return create_store("Checkout Store")


@pytest.fixture
def user(db):
    return User.objects.create_user(email="checkout@example.com", password="Str0ng!Passw0rd")


@pytest.fixture
def shipping_method(db, store):
    return ShippingMethod.objects.create(
        store=store, name="Post", code="POST", flat_price=Decimal("5.0000")
    )


@pytest.fixture
def payment_methods(db):
    from apps.checkout.models import ensure_default_payment_methods

    ensure_default_payment_methods()


@pytest.fixture
def published_product(store):
    product = create_product(store, "Checkout Product", price=PRICE, stock_quantity=50)
    publish_product(product)
    return product


@pytest.fixture
def customer_cart(store, user, published_product):
    cart = get_or_create_cart(store, user=user)
    add_to_cart(cart, published_product, 2)
    return cart


def _checkout(
    cart,
    user=None,
    email=None,
    shipping_address=None,
    shipping_method_code="POST",
    payment_method_code="cash_on_delivery",
    pipeline=None,
):
    return execute_checkout(
        cart,
        user=user,
        email=email or "",
        shipping_address=shipping_address if shipping_address is not None else dict(ADDRESS),
        shipping_method_code=shipping_method_code,
        payment_method_code=payment_method_code,
        pipeline=pipeline,
    )


def test_default_pipeline_step_order(db):
    pipeline = CheckoutPipeline()
    assert pipeline.step_names() == [
        "validate_cart",
        "customer",
        "address",
        "shipping",
        "tax",
        "discount",
        "inventory",
        "payment",
        "create_order",
    ]


def test_pipeline_plugin_extension_points():
    class FraudCheckStep:
        name = "fraud_check"
        ran = []

        def run(self, context):
            FraudCheckStep.ran.append("fraud")

    pipeline = CheckoutPipeline()
    pipeline.register_before("payment", FraudCheckStep())
    pipeline.register_after("create_order", FraudCheckStep())
    pipeline.append(FraudCheckStep())

    names = pipeline.step_names()
    assert names.index("fraud_check") == names.index("payment") - 1
    assert names[-2] == "fraud_check"
    assert names[-1] == "fraud_check"

    with pytest.raises(ValueError):
        pipeline.register_before("missing_step", FraudCheckStep())


def test_full_checkout_creates_order(store, user, customer_cart, published_product, shipping_method, payment_methods):
    order = _checkout(customer_cart, user=user)

    assert order.pk is not None
    assert order.status == Order.STATUS_PENDING
    assert order.user_id == user.id
    assert order.email == user.email
    assert order.subtotal == Decimal("200.0000")
    assert order.shipping_amount == Decimal("5.0000")
    assert order.tax_amount == Decimal("0.0000")
    assert order.total == Decimal("205.0000")
    assert order.shipping_method == "POST"
    assert order.payment_method == "cash_on_delivery"

    assert OrderItem.objects.filter(order=order).count() == 1
    item = OrderItem.objects.get(order=order)
    assert item.product_name == "Checkout Product"
    assert item.quantity == 2
    assert item.unit_price == PRICE

    address = OrderAddress.objects.get(order=order)
    assert address.address_type == OrderAddress.TYPE_SHIPPING
    assert address.city == "Tehran"
    assert address.country == "IR"

    customer_cart.refresh_from_db()
    assert customer_cart.status == Cart.STATUS_ORDERED


def test_order_numbers_are_unique(store, user, published_product, shipping_method, payment_methods):
    cart1 = get_or_create_cart(store, user=user)
    add_to_cart(cart1, published_product, 1)
    order1 = _checkout(cart1, user=user)

    user2 = User.objects.create_user(email="second@example.com", password="Str0ng!Passw0rd")
    cart2 = get_or_create_cart(store, user=user2)
    add_to_cart(cart2, published_product, 1)
    order2 = _checkout(cart2, user=user2)

    assert order1.number != order2.number


def test_guest_checkout_without_account(store, published_product, shipping_method, payment_methods):
    cart = get_or_create_cart(store, session_key="guest-checkout")
    add_to_cart(cart, published_product, 1)

    order = _checkout(cart, user=None, email="guest@example.com")

    assert order.user_id is None
    assert order.email == "guest@example.com"


def test_guest_checkout_requires_email(store, published_product, shipping_method, payment_methods):
    cart = get_or_create_cart(store, session_key="no-email")
    add_to_cart(cart, published_product, 1)

    with pytest.raises(ValidationError, match="email"):
        _checkout(cart, user=None, email="")


def test_checkout_empty_cart_fails(store, user, shipping_method, payment_methods):
    empty = get_or_create_cart(store, user=user)
    with pytest.raises(ValidationError, match="empty"):
        _checkout(empty, user=user)


def test_checkout_rejects_unavailable_product(store, user, published_product, shipping_method, payment_methods):
    cart = get_or_create_cart(store, user=user)
    add_to_cart(cart, published_product, 1)
    published_product.is_published = False
    published_product.save()

    with pytest.raises(ValidationError, match="no longer available"):
        _checkout(cart, user=user)


def test_checkout_rejects_insufficient_inventory(store, user, published_product, shipping_method, payment_methods):
    cart = get_or_create_cart(store, user=user)
    add_to_cart(cart, published_product, 5)

    warehouse = create_warehouse(store, "Checkout WH", "WH-CK")
    item = get_or_create_inventory(warehouse, product=published_product)
    receive_stock(item, 3)

    with pytest.raises(ConflictError, match="Insufficient"):
        _checkout(cart, user=user)


def test_checkout_reserves_inventory_stock(store, user, shipping_method, payment_methods):
    product = create_product(store, "Reserved Thing", product_type="variant")
    variant = add_variant(product, "RSV-1", Decimal("20.0000"))
    publish_product(product)

    warehouse = create_warehouse(store, "Reserve WH", "WH-RS")
    item = get_or_create_inventory(warehouse, variant=variant)
    receive_stock(item, 10)

    cart = get_or_create_cart(store, user=user)
    add_to_cart(cart, product, 3, variant=variant)

    order = _checkout(cart, user=user)

    item.refresh_from_db()
    assert item.reserved_quantity == 3
    assert item.available_quantity == 7
    assert order.items.first().sku == "RSV-1"


def test_checkout_decrements_fallback_stock(store, user, published_product, shipping_method, payment_methods):
    cart = get_or_create_cart(store, user=user)
    add_to_cart(cart, published_product, 3)

    _checkout(cart, user=user)

    published_product.refresh_from_db()
    assert published_product.stock_quantity == 47


def test_checkout_with_price_change_uses_current_price(
    store, user, customer_cart, published_product, shipping_method, payment_methods
):
    update_product(published_product, price=Decimal("120.0000"))

    order = _checkout(customer_cart, user=user)

    item = OrderItem.objects.get(order=order)
    assert item.unit_price == Decimal("120.0000")
    assert order.subtotal == Decimal("240.0000")


def test_checkout_with_tax(store, user, customer_cart, published_product, shipping_method, payment_methods):
    from apps.pricing.models import TaxClass
    from apps.pricing.taxes import create_tax_rate

    standard = TaxClass.objects.create(name="Std Tax", is_default=True)
    create_tax_rate(standard, "VAT", Decimal("9.0000"), country="IR")

    order = _checkout(customer_cart, user=user)

    assert order.tax_amount == Decimal("18.0000")
    assert order.total == Decimal("200.0000") - Decimal("0.0000") + Decimal("5.0000") + Decimal("18.0000")


def test_checkout_with_coupon_records_usage(
    store, user, customer_cart, published_product, shipping_method, payment_methods
):
    discount = Discount.objects.create(
        name="Checkout Deal", discount_type="percentage", value=Decimal("10"), scope="cart",
        coupon_code="CHECKOUT10",
    )
    attach_coupon(customer_cart, "checkout10", customer=user)

    order = _checkout(customer_cart, user=user)

    assert order.coupon_code == "CHECKOUT10"
    assert order.discount_amount == Decimal("20.0000")
    assert order.total == Decimal("200.0000") - Decimal("20.0000") + Decimal("5.0000")
    discount.refresh_from_db()
    assert discount.used_count == 1


def test_failed_checkout_does_not_create_partial_order(
    store, user, customer_cart, published_product, shipping_method, payment_methods
):
    class ExplodingStep:
        name = "explode"

        def run(self, context):
            raise RuntimeError("boom before order creation")

    pipeline = CheckoutPipeline()
    pipeline.register_before("create_order", ExplodingStep())

    with pytest.raises(RuntimeError):
        _checkout(customer_cart, user=user, pipeline=pipeline)

    assert Order.objects.count() == 0
    assert OrderItem.objects.count() == 0
    customer_cart.refresh_from_db()
    assert customer_cart.status == Cart.STATUS_ACTIVE


def test_failed_checkout_rolls_back_inventory_reservation(store, user, shipping_method, payment_methods):
    product = create_product(store, "Rollback Stock", product_type="variant")
    variant = add_variant(product, "RB-1", Decimal("20.0000"))
    publish_product(product)

    warehouse = create_warehouse(store, "RB WH", "WH-RB")
    item = get_or_create_inventory(warehouse, variant=variant)
    receive_stock(item, 10)

    cart = get_or_create_cart(store, user=user)
    add_to_cart(cart, product, 2, variant=variant)

    class ExplodingStep:
        name = "explode"

        def run(self, context):
            raise RuntimeError("boom after reservation")

    pipeline = CheckoutPipeline()
    pipeline.register_after("inventory", ExplodingStep())

    with pytest.raises(RuntimeError):
        _checkout(cart, user=user, pipeline=pipeline)

    item.refresh_from_db()
    assert item.reserved_quantity == 0


def test_inactive_customer_cannot_checkout(
    store, user, customer_cart, published_product, shipping_method, payment_methods
):
    user.is_active = False
    user.save()
    with pytest.raises(ValidationError, match="disabled"):
        _checkout(customer_cart, user=user)


def test_unavailable_shipping_method_rejected(store, user, customer_cart, published_product, payment_methods):
    ShippingMethod.objects.create(
        store=store, name="Disabled Post", code="DISABLED", flat_price=Decimal("9"), is_active=False
    )
    with pytest.raises(NotFoundError, match="shipping"):
        _checkout(customer_cart, user=user, shipping_method_code="DISABLED")


def test_unavailable_payment_method_rejected(
    store, user, customer_cart, published_product, shipping_method, payment_methods
):
    PaymentMethod.objects.create(name="Disabled Pay", code="disabled_pay", is_active=False)
    with pytest.raises(NotFoundError, match="payment"):
        _checkout(customer_cart, user=user, payment_method_code="disabled_pay")


def test_invalid_coupon_fails_checkout(store, user, customer_cart, published_product, shipping_method, payment_methods):
    from datetime import timedelta

    from django.utils import timezone

    expired = Discount.objects.create(
        name="Expired", discount_type="percentage", value=Decimal("10"), scope="cart",
        coupon_code="EXPIRED10", end_at=timezone.now() - timedelta(hours=1),
    )
    customer_cart.coupon = expired
    customer_cart.save(update_fields=["coupon"])

    with pytest.raises(ValidationError, match="expired"):
        _checkout(customer_cart, user=user)

    expired.refresh_from_db()
    assert expired.used_count == 0
    customer_cart.refresh_from_db()
    assert customer_cart.status == Cart.STATUS_ACTIVE
