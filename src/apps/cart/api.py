from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.cart.calculation import calculate_cart
from apps.cart.models import Cart, CartItem
from apps.cart.services import (
    add_to_cart,
    attach_coupon,
    clear_cart,
    get_or_create_cart,
    remove_coupon,
    remove_item,
    update_item_quantity,
)
from apps.catalog.models import Product, ProductVariant
from core.exceptions import NotFoundError


class CartItemSerializer(serializers.ModelSerializer):
    product = serializers.SlugRelatedField(slug_field="slug", read_only=True)
    variant = serializers.SlugRelatedField(slug_field="sku", read_only=True)

    class Meta:
        model = CartItem
        fields = ["id", "product", "variant", "quantity", "unit_price_at_add"]


class CartSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    lines = serializers.SerializerMethodField()
    subtotal = serializers.SerializerMethodField()
    discount_amount = serializers.SerializerMethodField()
    total = serializers.SerializerMethodField()
    coupon_code = serializers.SerializerMethodField()

    def _calculation(self, cart):
        if not hasattr(self, "_calc"):
            customer = cart.user
            self._calc = calculate_cart(cart, customer=customer)
        return self._calc

    def get_lines(self, cart):
        calculation = self._calculation(cart)
        return [
            {
                "item_id": line.item_id,
                "product_name": line.product_name,
                "quantity": line.quantity,
                "unit_price": str(line.unit_price),
                "line_total": str(line.line_total),
            }
            for line in calculation.lines
        ]

    def get_subtotal(self, cart):
        return str(self._calculation(cart).subtotal)

    def get_discount_amount(self, cart):
        return str(self._calculation(cart).discount_amount)

    def get_total(self, cart):
        return str(self._calculation(cart).total)

    def get_coupon_code(self, cart):
        return self._calculation(cart).coupon_code


class AddItemSerializer(serializers.Serializer):
    product = serializers.CharField()
    variant = serializers.CharField(required=False, allow_blank=True)
    quantity = serializers.IntegerField(min_value=1, default=1)


class UpdateItemSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=0)


class CouponSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=50)


def resolve_cart(request, *, create: bool = False) -> Cart | None:
    """Resolve the active cart for the caller.

    Authenticated callers get their cart; guests use the API session or an
    ``X-Cart-Session`` header value as the session key.
    """
    if request.user.is_authenticated:
        if create:
            return get_or_create_cart(_store(request), user=request.user)
        return _get_cart(request, user=request.user)
    session_key = request.headers.get("X-Cart-Session") or request.session.session_key
    if not session_key:
        if create:
            request.session.create()
            session_key = request.session.session_key
        else:
            return None
    if create:
        return get_or_create_cart(_store(request), session_key=session_key)
    return _get_cart(request, session_key=session_key)


def _store(request):
    from apps.stores.services import ensure_default_store

    store_slug = request.headers.get("X-Store") or request.query_params.get("store")
    if store_slug:
        from apps.stores.models import Store

        store = Store.objects.filter(slug=store_slug).first()
        if store is not None:
            return store
    return ensure_default_store()


def _get_cart(request, **kwargs):
    from apps.cart.services import get_cart

    return get_cart(_store(request), **kwargs)


class CartView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        cart = resolve_cart(request, create=True)
        return Response(CartSerializer(cart).data)

    def delete(self, request, *args, **kwargs):
        cart = resolve_cart(request)
        if cart is not None:
            clear_cart(cart)
        return Response(status=status.HTTP_204_NO_CONTENT)


class CartItemsView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = AddItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        cart = resolve_cart(request, create=True)
        product = Product.objects.filter(slug=data["product"]).first()
        if product is None:
            raise NotFoundError("Product not found", code="cart.product_not_found")
        variant = None
        if data.get("variant"):
            variant = ProductVariant.objects.filter(sku=data["variant"]).first()
            if variant is None:
                raise NotFoundError("Variant not found", code="cart.variant_not_found")
        add_to_cart(cart, product, data["quantity"], variant)
        return Response(CartSerializer(cart).data, status=status.HTTP_201_CREATED)


class CartItemDetailView(APIView):
    permission_classes = [AllowAny]

    def _cart(self, request) -> Cart:
        cart = resolve_cart(request)
        if cart is None:
            raise NotFoundError("Cart not found", code="cart.not_found")
        return cart

    def patch(self, request, item_id, *args, **kwargs):
        cart = self._cart(request)
        serializer = UpdateItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        update_item_quantity(cart, item_id, serializer.validated_data["quantity"])
        return Response(CartSerializer(cart).data)

    def delete(self, request, item_id, *args, **kwargs):
        cart = self._cart(request)
        remove_item(cart, item_id)
        return Response(status=status.HTTP_204_NO_CONTENT)


class CartCouponView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        cart = resolve_cart(request, create=True)
        serializer = CouponSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        attach_coupon(
            cart,
            serializer.validated_data["code"],
            customer=request.user if request.user.is_authenticated else None,
        )
        return Response(CartSerializer(cart).data)

    def delete(self, request, *args, **kwargs):
        cart = resolve_cart(request)
        if cart is not None:
            remove_coupon(cart)
        return Response(status=status.HTTP_204_NO_CONTENT)
