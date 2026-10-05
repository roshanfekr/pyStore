from decimal import Decimal

from django.db.models import F

from apps.cart.models import Cart
from apps.catalog.models import Product, ProductVariant
from apps.checkout.context import CheckoutContext, CheckoutLine
from apps.checkout.models import PaymentMethod, ShippingMethod
from apps.inventory.models import InventoryItem
from apps.inventory.services import reserve_stock
from apps.orders.models import Order, OrderAddress, OrderItem
from apps.pricing.discounts import apply_discount, record_usage, validate_discount
from apps.pricing.engine import resolve_product_price
from apps.pricing.taxes import calculate_tax
from core.exceptions import ConflictError, NotFoundError, ValidationError


class CheckoutStep:
    name = "step"

    def run(self, context: CheckoutContext) -> None:
        raise NotImplementedError


class ValidateCartStep(CheckoutStep):
    name = "validate_cart"

    def run(self, context: CheckoutContext) -> None:
        cart = Cart.objects.select_related("store", "coupon").get(pk=context.cart.pk)
        if cart.status != Cart.STATUS_ACTIVE:
            raise ValidationError("Cart is no longer active", code="checkout.cart_inactive")

        items = list(cart.items.select_related("product", "variant", "product__store"))
        if not items:
            raise ValidationError("Cart is empty", code="checkout.empty_cart")

        subtotal = Decimal("0.0000")
        for item in items:
            product = item.product
            if not product.is_published or product.store_id != cart.store_id:
                raise ValidationError(
                    f"Product {product.name!r} is no longer available",
                    code="checkout.product_unavailable",
                )
            try:
                unit_price = resolve_product_price(
                    product,
                    item.variant,
                    customer=context.user,
                    store=cart.store,
                    quantity=item.quantity,
                )
            except ValueError:
                raise ValidationError(
                    f"Product {product.name!r} has no valid price",
                    code="checkout.product_unavailable",
                ) from None

            price_changed = item.unit_price_at_add != unit_price
            line_total = (unit_price * item.quantity).quantize(Decimal("0.0001"))
            context.lines.append(
                CheckoutLine(
                    cart_item_id=str(item.id),
                    product=product,
                    variant=item.variant,
                    name=product.name,
                    sku=item.variant.sku if item.variant else product.sku,
                    quantity=item.quantity,
                    unit_price=unit_price,
                    line_total=line_total,
                    price_changed=price_changed,
                )
            )
            subtotal += line_total

        context.subtotal = subtotal


class CustomerStep(CheckoutStep):
    name = "customer"

    def run(self, context: CheckoutContext) -> None:
        if context.user is not None:
            if not context.user.is_active:
                raise ValidationError(
                    "Account is disabled", code="checkout.customer_disabled"
                )
            if not context.email:
                context.email = context.user.email
            return
        if not context.email or "@" not in context.email:
            raise ValidationError(
                "A valid email is required for guest checkout", code="checkout.email_required"
            )


class AddressStep(CheckoutStep):
    name = "address"

    REQUIRED_FIELDS = ("country", "city", "address_line")

    def run(self, context: CheckoutContext) -> None:
        address = context.shipping_address or {}
        missing = [f for f in self.REQUIRED_FIELDS if not str(address.get(f, "")).strip()]
        if missing:
            raise ValidationError(
                f"Address fields required: {', '.join(missing)}", code="checkout.address_required"
            )
        context.shipping_address = address


class ShippingStep(CheckoutStep):
    name = "shipping"

    def run(self, context: CheckoutContext) -> None:
        method = ShippingMethod.objects.filter(
            store=context.cart.store,
            code=context.shipping_method_code,
            is_active=True,
        ).first()
        if method is None:
            raise NotFoundError(
                "Selected shipping method is not available", code="checkout.shipping_unavailable"
            )
        context.shipping_amount = method.flat_price


class TaxStep(CheckoutStep):
    name = "tax"

    def run(self, context: CheckoutContext) -> None:
        address = context.shipping_address
        tax_total = Decimal("0.0000")
        for line in context.lines:
            result = calculate_tax(
                line.line_total,
                product=line.product,
                country=address.get("country", ""),
                state=address.get("state", ""),
                customer=context.user,
            )
            tax_total += result["tax_amount"]
        context.tax_amount = tax_total


class DiscountStep(CheckoutStep):
    name = "discount"

    def run(self, context: CheckoutContext) -> None:
        cart = Cart.objects.select_related("coupon").get(pk=context.cart.pk)
        if cart.coupon_id is None:
            return
        discount = cart.coupon
        validate_discount(discount, amount=context.subtotal, customer=context.user)
        application = apply_discount(
            discount, context.subtotal, customer=context.user,
        )
        context.discount_amount = application.amount
        context.coupon_code = discount.coupon_code


class InventoryStep(CheckoutStep):
    name = "inventory"

    def run(self, context: CheckoutContext) -> None:
        for line in context.lines:
            inventory_items = self._inventory_items(line)
            if not inventory_items:
                self._decrement_fallback_stock(line)
                continue

            sorted_items = sorted(inventory_items, key=lambda i: i.available_quantity, reverse=True)
            best = sorted_items[0]
            if best.available_quantity < line.quantity:
                raise ConflictError(
                    f"Insufficient stock for {line.name!r}", code="checkout.insufficient_stock"
                )
            reserve_stock(best, line.quantity, reference="checkout", note="Reserved at checkout")

    @staticmethod
    def _inventory_items(line: CheckoutLine):
        if line.variant is not None:
            return list(InventoryItem.objects.filter(variant=line.variant))
        return list(InventoryItem.objects.filter(product=line.product))

    @staticmethod
    def _decrement_fallback_stock(line: CheckoutLine) -> None:
        if line.variant is not None:
            current = ProductVariant.objects.filter(pk=line.variant.pk).values_list(
                "stock_quantity", flat=True
            ).first() or 0
            if current < line.quantity:
                raise ConflictError(
                    f"Insufficient stock for {line.name!r}", code="checkout.insufficient_stock"
                )
            ProductVariant.objects.filter(pk=line.variant.pk).update(
                stock_quantity=F("stock_quantity") - line.quantity
            )
        else:
            current = Product.objects.filter(pk=line.product.pk).values_list(
                "stock_quantity", flat=True
            ).first() or 0
            if current < line.quantity:
                raise ConflictError(
                    f"Insufficient stock for {line.name!r}", code="checkout.insufficient_stock"
                )
            Product.objects.filter(pk=line.product.pk).update(
                stock_quantity=F("stock_quantity") - line.quantity
            )


class PaymentStep(CheckoutStep):
    name = "payment"

    def run(self, context: CheckoutContext) -> None:
        method = PaymentMethod.objects.filter(
            code=context.payment_method_code, is_active=True
        ).first()
        if method is None:
            raise NotFoundError(
                "Selected payment method is not available", code="checkout.payment_unavailable"
            )


class OrderCreationStep(CheckoutStep):
    name = "create_order"

    def run(self, context: CheckoutContext) -> None:
        cart = context.cart
        order = Order.objects.create(
            store=cart.store,
            user=context.user,
            email=context.email,
            subtotal=context.subtotal,
            discount_amount=context.discount_amount,
            shipping_amount=context.shipping_amount,
            tax_amount=context.tax_amount,
            total=context.subtotal - context.discount_amount + context.shipping_amount + context.tax_amount,
            coupon_code=context.coupon_code or "",
            shipping_method=context.shipping_method_code,
            payment_method=context.payment_method_code,
            currency=cart.store.default_currency,
        )

        for line in context.lines:
            OrderItem.objects.create(
                order=order,
                product=line.product,
                variant=line.variant,
                product_name=line.name,
                sku=line.sku,
                quantity=line.quantity,
                unit_price=line.unit_price,
                line_total=line.line_total,
            )

        address = context.shipping_address
        OrderAddress.objects.create(
            order=order,
            address_type=OrderAddress.TYPE_SHIPPING,
            first_name=address.get("first_name", ""),
            last_name=address.get("last_name", ""),
            email=context.email,
            phone=address.get("phone", ""),
            country=address.get("country", ""),
            state=address.get("state", ""),
            city=address.get("city", ""),
            postal_code=address.get("postal_code", ""),
            address_line=address.get("address_line", ""),
        )

        if context.coupon_code:
            coupon = cart.coupon
            record_usage(coupon, user=context.user, reference=order.number)

        cart.status = Cart.STATUS_ORDERED
        cart.save(update_fields=["status"])

        context.order = order


def default_steps():
    return [
        ValidateCartStep(),
        CustomerStep(),
        AddressStep(),
        ShippingStep(),
        TaxStep(),
        DiscountStep(),
        InventoryStep(),
        PaymentStep(),
        OrderCreationStep(),
    ]
