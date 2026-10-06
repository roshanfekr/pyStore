from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.checkout.api import ShippingMethodSerializer
from apps.checkout.models import ShippingMethod
from core.exceptions import ValidationError


class ShippingMethodsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        from apps.cart.api import _store

        store = _store(request)
        methods = ShippingMethod.objects.filter(store=store, is_active=True)
        return Response(ShippingMethodSerializer(methods, many=True).data)


class RateQuoteSerializer(serializers.Serializer):
    provider_code = serializers.CharField(max_length=100)
    context = serializers.DictField(required=False, default=dict)


class RatesView(APIView):
    """Quote shipping rates through a registered shipping provider plugin."""

    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = RateQuoteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        from core.shipping.registry import shipping_provider_registry

        provider = shipping_provider_registry.get(
            serializer.validated_data["provider_code"]
        )
        if provider is None:
            raise ValidationError(
                "Shipping provider is not registered", code="shipping.provider_unavailable"
            )
        rates = provider.get_rates(serializer.validated_data.get("context", {}))
        return Response({"rates": rates})


class TrackShipmentSerializer(serializers.Serializer):
    provider_code = serializers.CharField(max_length=100)
    tracking_number = serializers.CharField(max_length=100)


class TrackingView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = TrackShipmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        from core.shipping.registry import shipping_provider_registry

        provider = shipping_provider_registry.get(
            serializer.validated_data["provider_code"]
        )
        if provider is None:
            raise ValidationError(
                "Shipping provider is not registered", code="shipping.provider_unavailable"
            )
        tracking = provider.get_tracking(serializer.validated_data["tracking_number"])
        return Response({"tracking": tracking})
