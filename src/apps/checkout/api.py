from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.cart.api import resolve_cart
from apps.checkout.models import PaymentMethod, ShippingMethod
from apps.checkout.services import execute_checkout
from core.exceptions import NotFoundError


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
    shipping_address = serializers.DictField(child=serializers.CharField(allow_blank=True))
    shipping_method_code = serializers.CharField(max_length=50)
    payment_method_code = serializers.CharField(max_length=50)


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
        order = execute_checkout(
            cart,
            user=request.user if request.user.is_authenticated else None,
            email=data["email"],
            shipping_address=data["shipping_address"],
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
