import uuid

from rest_framework import mixins, serializers
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from apps.orders.models import Order, OrderItem, OrderNote
from apps.orders.services import add_order_note, cancel_order, request_return
from core.api.filters import QueryParamFilterMixin
from core.exceptions import NotFoundError


class OrderItemSerializer(serializers.Serializer):
    product_name = serializers.CharField()
    sku = serializers.CharField()
    quantity = serializers.IntegerField()
    unit_price = serializers.DecimalField(max_digits=18, decimal_places=4)
    line_total = serializers.DecimalField(max_digits=18, decimal_places=4)


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            "id", "number", "store", "email", "status", "payment_status",
            "shipment_status", "subtotal", "discount_amount", "shipping_amount",
            "tax_amount", "total", "currency", "coupon_code", "shipping_method",
            "payment_method", "invoice_number", "created_at", "items",
        ]


class CancelOrderSerializer(serializers.Serializer):
    note = serializers.CharField(required=False, allow_blank=True, default="")


class ReturnItemSerializer(serializers.Serializer):
    order_item_id = serializers.CharField()
    quantity = serializers.IntegerField(min_value=1)


class ReturnRequestSerializer(serializers.Serializer):
    items = ReturnItemSerializer(many=True, allow_empty=False)
    reason = serializers.CharField(required=False, allow_blank=True, default="")


class OrderNoteSerializer(serializers.Serializer):
    note = serializers.CharField(allow_blank=False)


class OrderViewSet(QueryParamFilterMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, GenericViewSet):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    query_filters = {
        "status": "status",
        "payment_status": "payment_status",
        "shipment_status": "shipment_status",
    }
    ordering_fields = ("created_at", "total", "number")
    default_ordering = "-created_at"

    def get_queryset(self):
        queryset = Order.objects.prefetch_related("items")
        user = self.request.user
        if user.has_perm("order.view"):
            return queryset
        return queryset.filter(user=user)

    def get_object(self):
        identifier = str(self.kwargs.get("pk"))
        queryset = self.filter_queryset(self.get_queryset())
        order = queryset.filter(number=identifier).first()
        if order is None:
            try:
                order = queryset.filter(pk=uuid.UUID(identifier)).first()
            except ValueError:
                order = None
        if order is None:
            raise NotFoundError("Order not found", code="orders.not_found")
        return order

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None, *args, **kwargs):
        order = self.get_object()
        serializer = CancelOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        cancel_order(order, actor=request.user, note=serializer.validated_data["note"])
        order.refresh_from_db()
        return Response(OrderSerializer(order).data)

    @action(detail=True, methods=["post"])
    def returns(self, request, pk=None, *args, **kwargs):
        order = self.get_object()
        serializer = ReturnRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        items = []
        for spec in serializer.validated_data["items"]:
            order_item = OrderItem.objects.filter(order=order, pk=spec["order_item_id"]).first()
            if order_item is None:
                raise NotFoundError("Order item not found", code="orders.item_not_found")
            items.append((order_item, spec["quantity"]))
        return_request = request_return(
            order, items, user=request.user, reason=serializer.validated_data["reason"]
        )
        return Response(
            {"id": str(return_request.id), "status": return_request.status}, status=201
        )

    @action(detail=True, methods=["post"])
    def notes(self, request, pk=None, *args, **kwargs):
        order = self.get_object()
        serializer = OrderNoteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        note = add_order_note(
            order,
            serializer.validated_data["note"],
            note_type=OrderNote.TYPE_CUSTOMER,
            author=request.user,
        )
        return Response({"id": str(note.id)}, status=201)
