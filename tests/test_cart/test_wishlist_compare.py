from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.cart.compare import (
    add_to_compare,
    compare_list,
    remove_from_compare,
)
from apps.cart.services import get_or_create_cart
from apps.cart.wishlist import (
    add_to_wishlist,
    move_to_cart,
    remove_from_wishlist,
    wishlist_for,
)
from apps.catalog.services import create_product, publish_product
from apps.stores.services import create_store
from core.exceptions import ConflictError, ValidationError

User = get_user_model()

pytestmark = [pytest.mark.django_db]

PRICE = Decimal("100.0000")


@pytest.fixture
def store(db):
    return create_store("Wishlist Store")


@pytest.fixture
def user(db):
    return User.objects.create_user(email="wishful@example.com", password="Str0ng!Passw0rd")


def _product(store, name):
    product = create_product(store, name, price=PRICE, stock_quantity=50)
    publish_product(product)
    return product


def test_add_and_remove_wishlist(user, store):
    product = _product(store, "Wished")

    add_to_wishlist(user, product)
    assert wishlist_for(user).count() == 1

    with pytest.raises(ConflictError):
        add_to_wishlist(user, product)

    remove_from_wishlist(user, product)
    assert wishlist_for(user).count() == 0


def test_move_wishlist_item_to_cart(user, store):
    product = _product(store, "Moved Thing")
    add_to_wishlist(user, product)

    item = move_to_cart(user, product, store=store, quantity=2)

    assert item.quantity == 2
    assert wishlist_for(user).count() == 0
    cart = get_or_create_cart(store, user=user)
    assert cart.items.filter(product=product, quantity=2).exists()


def test_compare_add_and_list(user, store):
    a = _product(store, "Compare A")
    b = _product(store, "Compare B")

    add_to_compare(a, user=user)
    add_to_compare(b, user=user)

    items = compare_list(user=user)
    assert {item.product.name for item in items} == {"Compare A", "Compare B"}


def test_compare_duplicate_rejected(user, store):
    product = _product(store, "Compare Dup")
    add_to_compare(product, user=user)
    with pytest.raises(ConflictError):
        add_to_compare(product, user=user)


def test_compare_limit(user, store):
    for index in range(4):
        add_to_compare(_product(store, f"Limit {index}"), user=user)
    with pytest.raises(ConflictError, match="limited"):
        add_to_compare(_product(store, "Limit 5"), user=user)


def test_compare_remove(user, store):
    product = _product(store, "Remove Me")
    add_to_compare(product, user=user)
    remove_from_compare(product, user=user)
    assert compare_list(user=user).count() == 0


def test_compare_guest_by_session(store):
    product = _product(store, "Guest Compare")
    add_to_compare(product, session_key="guest-sess")
    assert compare_list(session_key="guest-sess").count() == 1

    with pytest.raises(ValidationError):
        add_to_compare(_product(store, "No Identity"))


def test_wishlist_requires_published_product(user, store):
    draft = create_product(store, "Draft Product", price=PRICE)
    with pytest.raises(ValidationError):
        add_to_wishlist(user, draft)
