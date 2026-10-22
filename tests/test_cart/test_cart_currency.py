from decimal import Decimal

import pytest

from apps.cart.services import (
    add_to_cart,
    cart_currency,
    ensure_cart_currency,
    get_or_create_cart,
)
from apps.catalog.services import create_product, publish_product
from apps.pricing.models import ProductPrice
from apps.stores.services import create_store

pytestmark = [pytest.mark.django_db]


@pytest.fixture
def store(db):
    return create_store("Cart Currency Store")


@pytest.fixture
def product(store):
    product = create_product(store, "Currency Cart Product", price=Decimal("100.0000"), stock_quantity=10)
    publish_product(product)
    return product


def test_new_carts_default_to_the_store_base_currency(store):
    cart = get_or_create_cart(store, session_key="legacy-session")
    assert cart.currency == store.default_currency
    assert cart_currency(cart) == "IRT"


def test_cart_can_be_created_in_the_active_currency(store):
    cart = get_or_create_cart(store, session_key="usd-session", currency="usd")
    assert cart.currency == "USD"


def test_add_to_cart_uses_the_explicit_currency_price(store, product):
    ProductPrice.objects.create(product=product, currency="USD", price=Decimal("18.0000"))
    cart = get_or_create_cart(store, session_key="usd-session", currency="USD")

    item = add_to_cart(cart, product, 2)

    assert item.unit_price_at_add == Decimal("18.0000")


def test_add_to_cart_without_explicit_price_is_rejected(store, product):
    cart = get_or_create_cart(store, session_key="usd-session", currency="USD")

    with pytest.raises(Exception) as error:
        add_to_cart(cart, product, 1)
    assert getattr(error.value, "code", "") == "cart.price_unavailable"


def test_add_to_cart_falls_back_to_the_base_currency_price(store, product):
    cart = get_or_create_cart(store, session_key="irt-session")

    item = add_to_cart(cart, product, 1)

    assert item.unit_price_at_add == Decimal("100.0000")


def test_empty_cart_adopts_the_requested_currency(store):
    cart = get_or_create_cart(store, session_key="switch-session")

    ensure_cart_currency(cart, "USD")

    cart.refresh_from_db()
    assert cart.currency == "USD"


def test_cart_with_lines_refuses_another_currency(store, product):
    cart = get_or_create_cart(store, session_key="mismatch-session")
    add_to_cart(cart, product, 1)

    with pytest.raises(Exception) as error:
        ensure_cart_currency(cart, "USD")
    assert getattr(error.value, "code", "") == "cart.currency_mismatch"
    cart.refresh_from_db()
    assert cart.currency == "IRT"


def test_legacy_cart_without_currency_is_a_base_currency_cart(store, product):
    cart = get_or_create_cart(store, session_key="legacy-session")
    cart.currency = None
    cart.save(update_fields=["currency"])

    add_to_cart(cart, product, 1)

    assert cart_currency(cart) == "IRT"
    assert cart.items.first().unit_price_at_add == Decimal("100.0000")


def test_ensure_cart_currency_is_a_noop_for_the_same_currency(store):
    cart = get_or_create_cart(store, session_key="same-session", currency="USD")

    ensure_cart_currency(cart, "USD")

    assert cart.currency == "USD"
