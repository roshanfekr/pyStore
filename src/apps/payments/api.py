import uuid

from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.checkout.models import PaymentMethod
from apps.orders.models import Order
from core.exceptions import NotFoundError, ValidationError


class InitializePaymentSerializer(serializers.Serializer):
    order = serializers.CharField()


class InitializePaymentView(APIView):
    """Initialize payment for an order through the registered gateway plugin."""

    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = InitializePaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = self._resolve_order(serializer.validated_data["order"], request.user)
        method = PaymentMethod.objects.filter(
            code=order.payment_method, is_active=True
        ).first()
        if method is None:
            raise ValidationError(
                "Payment method is not available", code="payments.method_unavailable"
            )
        from core.payments.registry import payment_gateway_registry

        gateway = payment_gateway_registry.get(order.payment_method)
        if gateway is None:
            raise ValidationError(
                "No payment gateway registered for this method",
                code="payments.gateway_unavailable",
            )
        result = gateway.initialize_payment(order)
        return Response(
            {
                "successful": result.successful,
                "reference": result.reference,
                "message": result.message,
            },
            status=status.HTTP_200_OK if result.successful else status.HTTP_402_PAYMENT_REQUIRED,
        )

    @staticmethod
    def _resolve_order(identifier: str, user) -> Order:
        order = Order.objects.filter(number=identifier).first()
        if order is None:
            try:
                order = Order.objects.filter(pk=uuid.UUID(identifier)).first()
            except ValueError:
                order = None
        if order is None:
            raise NotFoundError("Order not found", code="payments.order_not_found")
        if order.user_id != user.id and not user.has_perm("order.view"):
            raise NotFoundError("Order not found", code="payments.order_not_found")
        return order
