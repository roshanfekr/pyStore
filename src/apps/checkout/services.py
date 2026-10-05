
from apps.cart.models import Cart
from apps.checkout.context import CheckoutContext
from apps.checkout.models import ensure_default_payment_methods
from apps.checkout.pipeline import CheckoutPipeline
from core.infrastructure import atomic


@atomic()
def execute_checkout(
    cart: Cart,
    *,
    user=None,
    email: str = "",
    shipping_address: dict | None = None,
    shipping_method_code: str = "",
    payment_method_code: str = "",
    pipeline: CheckoutPipeline | None = None,
):
    cart = Cart.objects.select_related("store", "coupon").get(pk=cart.pk)
    context = CheckoutContext(
        cart=cart,
        user=user,
        email=email or (getattr(user, "email", "") or "" if user is not None else ""),
        shipping_address=shipping_address or {},
        shipping_method_code=shipping_method_code,
        payment_method_code=payment_method_code,
    )
    pipeline = pipeline if pipeline is not None else CheckoutPipeline()
    pipeline.run(context)
    return context.order


def ensure_checkout_defaults() -> None:
    ensure_default_payment_methods()
