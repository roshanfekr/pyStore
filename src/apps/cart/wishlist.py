from django.db import transaction

from apps.cart.models import WishlistItem
from apps.cart.services import add_to_cart, get_or_create_cart
from core.exceptions import ConflictError, ValidationError


def add_to_wishlist(user, product) -> WishlistItem:
    if not product.is_published:
        raise ValidationError("Product is not published", code="wishlist.product_unpublished")
    if WishlistItem.objects.filter(user=user, product=product).exists():
        raise ConflictError("Product is already in the wishlist", code="wishlist.duplicate")
    return WishlistItem.objects.create(user=user, product=product)


def remove_from_wishlist(user, product) -> None:
    WishlistItem.objects.filter(user=user, product=product).delete()


def move_to_cart(user, product, *, store, quantity: int = 1, variant=None):
    with transaction.atomic():
        item = add_to_cart(get_or_create_cart(store, user=user), product, quantity, variant)
        WishlistItem.objects.filter(user=user, product=product).delete()
    return item


def wishlist_for(user):
    return WishlistItem.objects.filter(user=user).select_related("product")
