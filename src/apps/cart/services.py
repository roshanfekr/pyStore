from django.db import transaction

from apps.cart.calculation import calculate_cart
from apps.cart.models import Cart, CartItem
from apps.catalog.models import DIGITAL_TYPES, Product
from apps.inventory.models import InventoryItem
from apps.pricing.discounts import get_discount_by_coupon, validate_discount
from apps.pricing.engine import resolve_product_price
from core.exceptions import ConflictError, NotFoundError, ValidationError


def get_or_create_cart(store, *, user=None, session_key=None) -> Cart:
    if user is not None:
        cart = Cart.objects.filter(store=store, user=user, status=Cart.STATUS_ACTIVE).first()
        if cart is None:
            cart = Cart.objects.create(store=store, user=user, status=Cart.STATUS_ACTIVE)
        return cart
    if not session_key:
        raise ValidationError(
            "Guest cart requires a session key", code="cart.session_required"
        )
    cart = Cart.objects.filter(
        store=store, session_key=session_key, status=Cart.STATUS_ACTIVE
    ).first()
    if cart is None:
        cart = Cart.objects.create(
            store=store, session_key=session_key, status=Cart.STATUS_ACTIVE
        )
    return cart


def get_cart(store, *, user=None, session_key=None) -> Cart | None:
    if user is not None:
        return Cart.objects.filter(store=store, user=user, status=Cart.STATUS_ACTIVE).first()
    if session_key:
        return Cart.objects.filter(
            store=store, session_key=session_key, status=Cart.STATUS_ACTIVE
        ).first()
    return None


def available_quantity_for(product: Product, variant=None) -> int | None:
    if product.product_type in DIGITAL_TYPES:
        return None
    if variant is not None:
        items = InventoryItem.objects.filter(variant=variant)
    else:
        items = InventoryItem.objects.filter(product=product)
    if items.exists():
        return sum(inventory.available_quantity for inventory in items)
    if variant is not None:
        return variant.stock_quantity
    return product.stock_quantity


def _validate_add(cart: Cart, product: Product, variant, quantity: int) -> None:
    if not product.is_published:
        raise ValidationError("Product is not published", code="cart.product_unpublished")
    if product.store_id != cart.store_id:
        raise ValidationError("Product belongs to another store", code="cart.store_mismatch")
    if product.product_type == "variant" and variant is None:
        raise ValidationError("A variant must be selected", code="cart.variant_required")
    if product.product_type != "variant" and variant is not None:
        raise ValidationError("This product has no variants", code="cart.variant_not_allowed")
    if variant is not None and variant.product_id != product.id:
        raise ValidationError("Variant does not belong to this product", code="cart.variant_mismatch")

    try:
        resolve_product_price(product, variant, store=cart.store, quantity=quantity)
    except ValueError:
        raise ValidationError(
            "Product price is not configured", code="cart.no_price"
        ) from None

    available = available_quantity_for(product, variant)
    if available is not None:
        existing = cart.items.filter(product=product, variant=variant).first()
        requested = quantity + (existing.quantity if existing else 0)
        if requested > available:
            raise ConflictError(
                f"Only {available} item(s) available", code="cart.insufficient_stock"
            )


@transaction.atomic
def add_to_cart(cart: Cart, product: Product, quantity: int = 1, variant=None) -> CartItem:
    if quantity <= 0:
        raise ValidationError("Quantity must be positive", code="cart.bad_quantity")
    _validate_add(cart, product, variant, quantity)

    unit_price = resolve_product_price(
        product, variant, store=cart.store, quantity=quantity
    )
    item = cart.items.filter(product=product, variant=variant).first()
    if item is not None:
        item.quantity += quantity
        item.save(update_fields=["quantity"])
    else:
        item = CartItem.objects.create(
            cart=cart,
            product=product,
            variant=variant,
            quantity=quantity,
            unit_price_at_add=unit_price,
        )
    return item


def _get_cart_item(cart: Cart, item_id) -> CartItem:
    item = cart.items.filter(pk=item_id).first()
    if item is None:
        raise NotFoundError("Cart item not found", code="cart.item_not_found")
    return item


def update_item_quantity(cart: Cart, item_id, quantity: int) -> CartItem:
    item = _get_cart_item(cart, item_id)
    if quantity <= 0:
        item.delete()
        return item
    available = available_quantity_for(item.product, item.variant)
    if available is not None and quantity > available:
        raise ConflictError(f"Only {available} item(s) available", code="cart.insufficient_stock")
    item.quantity = quantity
    item.save(update_fields=["quantity"])
    return item


def remove_item(cart: Cart, item_id) -> None:
    item = _get_cart_item(cart, item_id)
    item.delete()


def clear_cart(cart: Cart) -> None:
    cart.items.all().delete()
    cart.coupon = None
    cart.save(update_fields=["coupon"])


def attach_coupon(cart: Cart, code: str, *, customer=None) -> Cart:
    discount = get_discount_by_coupon(code)
    validate_discount(discount, customer=customer)
    cart.coupon = discount
    cart.save(update_fields=["coupon"])
    return cart


def remove_coupon(cart: Cart) -> Cart:
    cart.coupon = None
    cart.save(update_fields=["coupon"])
    return cart


def calculate(cart: Cart, *, customer=None):
    return calculate_cart(cart, customer=customer)


def merge_guest_cart(store, session_key: str, user) -> Cart:
    guest_cart = get_cart(store, session_key=session_key)
    user_cart = get_or_create_cart(store, user=user)
    if guest_cart is None:
        return user_cart

    for item in guest_cart.items.all():
        try:
            add_to_cart(user_cart, item.product, item.quantity, item.variant)
        except (ValidationError, ConflictError):
            continue

    coupon = guest_cart.coupon
    if coupon is not None and user_cart.coupon_id is None:
        user_cart.coupon = coupon
        user_cart.save(update_fields=["coupon"])

    guest_cart.hard_delete()
    return user_cart


def deactivate_cart(cart: Cart) -> Cart:
    cart.status = Cart.STATUS_ORDERED
    cart.save(update_fields=["status"])
    return cart
