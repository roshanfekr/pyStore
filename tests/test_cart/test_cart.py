from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.cart.calculation import calculate_cart
from apps.cart.models import Cart
from apps.cart.services import (
    add_to_cart,
    attach_coupon,
    available_quantity_for,
    clear_cart,
    get_or_create_cart,
    merge_guest_cart,
    remove_coupon,
    remove_item,
    update_item_quantity,
)
from apps.catalog.services import add_variant, create_product, publish_product, update_product
from apps.inventory.services import get_or_create_inventory, receive_stock
from apps.pricing.models import Discount
from apps.stores.services import create_store
from core.exceptions import ConflictError, ValidationError

User = get_user_model()

pytestmark = [pytest.mark.django_db]

PRICE = Decimal("100.0000")


@pytest.fixture
def store(db):
    return create_store("Cart Store")


@pytest.fixture
def other_store(db):
    return create_store("Other Cart Store")


@pytest.fixture
def user(db):
    return User.objects.create_user(email="shopper@example.com", password="Str0ng!Passw0rd")


@pytest.fixture
def published_product(store):
    product = create_product(store, "Cart Product", price=PRICE, stock_quantity=100)
    publish_product(product)
    return product


@pytest.fixture
def cart(store, user):
    return get_or_create_cart(store, user=user)


def test_cart_is_persistent_and_reused(store, user, cart):
    again = get_or_create_cart(store, user=user)
    assert again.id == cart.id
    assert Cart.objects.filter(user=user).count() == 1


def test_separate_carts_per_store(store, other_store, user, cart):
    other = get_or_create_cart(other_store, user=user)
    assert cart.id != other.id


def test_guest_cart_by_session(store):
    guest = get_or_create_cart(store, session_key="sess-123")
    assert guest.user_id is None
    again = get_or_create_cart(store, session_key="sess-123")
    assert again.id == guest.id


def test_guest_cart_requires_session_key(store):
    with pytest.raises(ValidationError):
        get_or_create_cart(store)


def test_add_to_cart(store, user, cart, published_product):
    item = add_to_cart(cart, published_product, 2)

    assert item.quantity == 2
    assert item.unit_price_at_add == PRICE
    assert cart.items.count() == 1


def test_add_merges_duplicate_items(cart, published_product):
    add_to_cart(cart, published_product, 1)
    item = add_to_cart(cart, published_product, 3)
    assert item.quantity == 4
    assert cart.items.count() == 1


def test_add_unpublished_product_rejected(store, cart):
    product = create_product(store, "Hidden", price=PRICE)
    with pytest.raises(ValidationError, match="not published"):
        add_to_cart(cart, product)


def test_add_product_from_other_store_rejected(store, other_store, cart):
    foreign = create_product(other_store, "Foreign Product", price=PRICE, stock_quantity=10)
    publish_product(foreign)
    with pytest.raises(ValidationError, match="another store"):
        add_to_cart(cart, foreign)


def test_add_product_without_price_rejected(store, cart):
    bundle = create_product(store, "Bundle Thing", product_type="bundled")
    child = create_product(store, "Bundle Child", price=PRICE)
    from apps.catalog.services import add_bundle_item

    add_bundle_item(bundle, child)
    publish_product(bundle)
    with pytest.raises(ValidationError, match="price"):
        add_to_cart(cart, bundle)


def test_variant_required_for_variant_products(store, cart):
    product = create_product(store, "Variant Cart Product", product_type="variant")
    variant = add_variant(product, "VCP-1", Decimal("20.0000"), stock_quantity=50)
    publish_product(product)

    with pytest.raises(ValidationError, match="variant"):
        add_to_cart(cart, product)

    item = add_to_cart(cart, product, 1, variant=variant)
    assert item.variant_id == variant.id

    simple = create_product(store, "Plain Simple", price=PRICE)
    publish_product(simple)
    with pytest.raises(ValidationError, match="no variants"):
        add_to_cart(cart, simple, 1, variant=variant)


def test_inventory_validation_with_inventory_items(store, cart):
    product = create_product(store, "Stocked Thing", product_type="variant")
    variant = add_variant(product, "STK-1", Decimal("10.0000"))
    publish_product(product)
    warehouse = None
    from apps.inventory.services import create_warehouse

    warehouse = create_warehouse(store, "WH", "WH-CART")
    get_or_create_inventory(warehouse, variant=variant)
    receive_stock(inventory_for_variant_helper(variant), 5)

    add_to_cart(cart, product, 4, variant=variant)
    with pytest.raises(ConflictError, match="available"):
        add_to_cart(cart, product, 2, variant=variant)


def inventory_for_variant_helper(variant):
    from apps.inventory.services import inventory_for_variant

    return inventory_for_variant(variant)


def test_inventory_fallback_to_variant_stock(store, cart):
    product = create_product(store, "Fallback Stock", product_type="variant")
    variant = add_variant(product, "FB-1", Decimal("10.0000"), stock_quantity=2)
    publish_product(product)

    assert available_quantity_for(product, variant) == 2
    with pytest.raises(ConflictError):
        add_to_cart(cart, product, 3, variant=variant)
    add_to_cart(cart, product, 2, variant=variant)


def test_digital_products_skip_inventory_check(store, cart):
    product = create_product(store, "Digital Thing", product_type="digital", price=PRICE)
    publish_product(product)
    assert available_quantity_for(product) is None
    item = add_to_cart(cart, product, 999)
    assert item.quantity == 999


def test_update_item_quantity_and_remove(cart, published_product):
    item = add_to_cart(cart, published_product, 2)
    updated = update_item_quantity(cart, item.id, 5)
    assert updated.quantity == 5

    update_item_quantity(cart, item.id, 0)
    assert cart.items.count() == 0


def test_update_quantity_rejects_over_stock(store, cart, published_product):
    published_product.stock_quantity = 3
    published_product.save()
    item = add_to_cart(cart, published_product, 2)

    with pytest.raises(ConflictError):
        update_item_quantity(cart, item.id, 10)


def test_remove_item(cart, published_product):
    item = add_to_cart(cart, published_product, 1)
    remove_item(cart, item.id)
    assert cart.items.count() == 0


def test_price_recalculation_reflects_changes(cart, published_product):
    add_to_cart(cart, published_product, 2)

    update_product(published_product, price=Decimal("150.0000"))

    calculation = calculate_cart(cart)
    assert calculation.subtotal == Decimal("300.0000")
    assert calculation.total == Decimal("300.0000")
    assert calculation.lines[0].unit_price == Decimal("150.0000")


def test_cart_calculation_sums_lines(cart, published_product, store):
    other = create_product(store, "Second Line", price=Decimal("50.0000"), stock_quantity=100)
    publish_product(other)
    add_to_cart(cart, published_product, 2)
    add_to_cart(cart, other, 3)

    calculation = calculate_cart(cart)

    assert len(calculation.lines) == 2
    assert calculation.subtotal == Decimal("350.0000")
    assert calculation.total == Decimal("350.0000")


def test_discount_application_in_calculation(store, cart, published_product, user):
    add_to_cart(cart, published_product, 2)

    discount = Discount.objects.create(
        name="10 Percent", discount_type="percentage", value=Decimal("10"), scope="cart",
        coupon_code="10P",
    )
    cart.coupon = discount
    cart.save(update_fields=["coupon"])

    calculation = calculate_cart(cart, customer=user)

    assert calculation.discount_amount == Decimal("20.0000")
    assert calculation.total == Decimal("180.0000")
    assert calculation.coupon_code == "10P"


def test_attach_and_remove_coupon(cart, published_product, user):
    add_to_cart(cart, published_product, 1)
    Discount.objects.create(
        name="Coupon Five", discount_type="fixed_amount", value=Decimal("5"), scope="cart",
        coupon_code="FIVE",
    )

    cart = attach_coupon(cart, "five", customer=user)
    assert cart.coupon.coupon_code == "FIVE"

    cart = remove_coupon(cart)
    assert cart.coupon_id is None


def test_invalid_coupon_rejected_at_attach(cart, published_product, user):
    from core.exceptions import NotFoundError

    add_to_cart(cart, published_product, 1)
    with pytest.raises(NotFoundError):
        attach_coupon(cart, "does-not-exist", customer=user)


def test_expired_coupon_fails_calculation(cart, published_product, user):
    from datetime import timedelta

    from django.utils import timezone

    add_to_cart(cart, published_product, 1)
    Discount.objects.create(
        name="Old Coupon", discount_type="percentage", value=Decimal("10"), scope="cart",
        coupon_code="OLD", end_at=timezone.now() - timedelta(hours=1),
    )
    cart.coupon = Discount.objects.get(coupon_code="OLD")
    cart.save(update_fields=["coupon"])

    with pytest.raises(ValidationError, match="expired"):
        calculate_cart(cart, customer=user)


def test_merge_guest_cart_into_customer_cart(store, user, published_product):
    guest = get_or_create_cart(store, session_key="merge-sess")
    add_to_cart(guest, published_product, 2)

    discount = Discount.objects.create(
        name="Merge Coupon", discount_type="percentage", value=Decimal("5"), scope="cart",
        coupon_code="MERGE5",
    )
    guest.coupon = discount
    guest.save(update_fields=["coupon"])

    user_cart = get_or_create_cart(store, user=user)
    add_to_cart(user_cart, published_product, 1)

    merged = merge_guest_cart(store, "merge-sess", user)

    assert merged.id == user_cart.id
    assert merged.items.get(product=published_product).quantity == 3
    assert merged.coupon_id == discount.id
    assert Cart.objects.filter(session_key="merge-sess").exists() is False


def test_merge_skips_unavailable_items(store, user, published_product):
    guest = get_or_create_cart(store, session_key="merge-skip")
    hidden = create_product(store, "Now Hidden", price=PRICE, stock_quantity=10)
    publish_product(hidden)
    add_to_cart(guest, hidden, 1)
    hidden.is_published = False
    hidden.save()
    add_to_cart(guest, published_product, 1)

    merged = merge_guest_cart(store, "merge-skip", user)

    assert merged.items.filter(product=hidden).exists() is False
    assert merged.items.filter(product=published_product).exists() is True


def test_clear_cart(cart, published_product):
    add_to_cart(cart, published_product, 1)
    clear_cart(cart)
    assert cart.items.count() == 0
    assert cart.coupon_id is None


def test_record_usage_not_needed_for_attach():
    discount = Discount.objects.create(
        name="Usage Check", discount_type="percentage", value=Decimal("10"), scope="cart"
    )
    assert discount.used_count == 0
