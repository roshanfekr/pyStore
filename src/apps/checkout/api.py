from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.cart.api import resolve_cart
from apps.checkout.models import PaymentMethod, ShippingMethod
from apps.checkout.services import execute_checkout
from apps.identity.models import Customer
from apps.identity.services.addresses import get_address
from core.exceptions import NotFoundError, ValidationError


class ShippingMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShippingMethod
        fields = ["code", "name", "store", "flat_price", "is_active"]


class PaymentMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentMethod
        fields = ["code", "name", "is_active"]


class CheckoutSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False, allow_blank=True, default="")
    shipping_address = serializers.DictField(
        child=serializers.CharField(allow_blank=True), required=False, default=dict
    )
    shipping_address_id = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    shipping_method_code = serializers.CharField(max_length=50)
    payment_method_code = serializers.CharField(max_length=50)

    def validate(self, attrs):
        if not attrs.get("shipping_address") and not attrs.get("shipping_address_id"):
            raise serializers.ValidationError(
                {"shipping_address": "Provide a shipping address or a saved address id."}
            )
        return attrs


class CheckoutMethodsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        from apps.cart.api import _store

        store = _store(request)
        shipping = ShippingMethod.objects.filter(store=store, is_active=True)
        payment = PaymentMethod.objects.filter(is_active=True)
        return Response(
            {
                "shipping_methods": ShippingMethodSerializer(shipping, many=True).data,
                "payment_methods": PaymentMethodSerializer(payment, many=True).data,
            }
        )


class CheckoutView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = CheckoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        cart = resolve_cart(request)
        if cart is None:
            raise NotFoundError("Cart not found", code="checkout.cart_not_found")
        email = data["email"]
        shipping_address = data["shipping_address"]
        address_id = data.get("shipping_address_id")
        if address_id:
            # A saved address may only be selected by the customer who owns it
            # (FR-CHK-001); the selected address is copied into the order
            # snapshot by the checkout pipeline.
            customer = (
                Customer.objects.filter(user=request.user).first()
                if request.user.is_authenticated
                else None
            )
            if customer is None:
                raise ValidationError(
                    "Sign in to use a saved address",
                    code="checkout.address_requires_authentication",
                )
            address = get_address(customer, address_id)
            shipping_address = address.as_snapshot()
            email = email or address.email
        order = execute_checkout(
            cart,
            user=request.user if request.user.is_authenticated else None,
            email=email,
            shipping_address=shipping_address,
            shipping_method_code=data["shipping_method_code"],
            payment_method_code=data["payment_method_code"],
        )
        return Response(
            {
                "order_number": order.number,
                "status": order.status,
                "total": str(order.total),
                "currency": order.currency,
            },
            status=status.HTTP_201_CREATED,
        )
