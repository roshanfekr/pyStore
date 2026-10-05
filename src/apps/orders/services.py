import uuid
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.catalog.models import DIGITAL_TYPES
from apps.identity.services.roles import ensure_permission
from apps.inventory.models import InventoryItem
from apps.inventory.services import release_stock
from apps.orders.models import (
    Order,
    OrderItem,
    OrderNote,
    OrderStatusLog,
    Refund,
    ReturnRequest,
    ReturnRequestItem,
)
from apps.orders.state_machine import (
    OrderStateMachine,
    validate_payment_transition,
    validate_shipment_transition,
)
from core.exceptions import ConflictError, NotFoundError, ValidationError

ORDER_PERMISSIONS = [
    ("order.view", "View orders"),
    ("order.edit", "Edit orders"),
    ("order.cancel", "Cancel orders"),
    ("order.refund", "Refund orders"),
]


def ensure_order_permissions() -> None:
    for codename, display_name in ORDER_PERMISSIONS:
        ensure_permission(codename, display_name=display_name, source="core")


def _log_status(order, *, status_type, from_value, to_value, actor=None, note="") -> None:
    OrderStatusLog.objects.create(
        order=order,
        status_type=status_type,
        from_value=from_value or "",
        to_value=to_value,
        note=note,
        actor=actor,
    )


def transition_order_status(order: Order, to_status: str, *, actor=None, note: str = "") -> Order:
    OrderStateMachine.validate_transition(order.status, to_status)
    from_status = order.status
    order.status = to_status
    order.save(update_fields=["status"])
    _log_status(
        order, status_type=OrderStatusLog.TYPE_ORDER, from_value=from_status,
        to_value=to_status, actor=actor, note=note,
    )
    return order


def set_payment_status(order: Order, to_status: str, *, actor=None, note: str = "") -> Order:
    validate_payment_transition(order.payment_status, to_status)
    from_status = order.payment_status
    order.payment_status = to_status
    order.save(update_fields=["payment_status"])
    _log_status(
        order, status_type=OrderStatusLog.TYPE_PAYMENT, from_value=from_status,
        to_value=to_status, actor=actor, note=note,
    )
    return order


def set_shipment_status(order: Order, to_status: str, *, actor=None, note: str = "") -> Order:
    validate_shipment_transition(order.shipment_status, to_status)
    from_status = order.shipment_status
    order.shipment_status = to_status
    order.save(update_fields=["shipment_status"])
    _log_status(
        order, status_type=OrderStatusLog.TYPE_SHIPMENT, from_value=from_status,
        to_value=to_status, actor=actor, note=note,
    )
    return order


def _restock(order_item: OrderItem, quantity: int) -> None:
    if order_item.product and order_item.product.product_type in DIGITAL_TYPES:
        return

    if order_item.variant_id:
        inventory_items = InventoryItem.objects.filter(variant=order_item.variant)
    else:
        inventory_items = InventoryItem.objects.filter(product=order_item.product)

    with_reserved = sorted(inventory_items, key=lambda i: i.reserved_quantity, reverse=True)
    if with_reserved and with_reserved[0].reserved_quantity > 0:
        release_stock(with_reserved[0], quantity, reference="order-cancelled")
        return

    if order_item.variant_id:
        from apps.catalog.models import ProductVariant

        ProductVariant.objects.filter(pk=order_item.variant_id).update(
            stock_quantity=models_f_increment(quantity)
        )
    elif order_item.product_id:
        from apps.catalog.models import Product

        Product.objects.filter(pk=order_item.product_id).update(
            stock_quantity=models_f_increment(quantity)
        )


def models_f_increment(quantity: int):
    from django.db.models import F

    return F("stock_quantity") + quantity


def _recalculate_totals(order: Order, cancelled_amount: Decimal) -> None:
    order.subtotal = max(order.subtotal - cancelled_amount, Decimal("0.0000"))
    order.total = max(order.total - cancelled_amount, Decimal("0.0000"))
    order.save(update_fields=["subtotal", "total"])


def cancel_order(order: Order, *, actor=None, note: str = "") -> Order:
    OrderStateMachine.validate_transition(order.status, Order.STATUS_CANCELLED)

    for item in order.items.all():
        remaining = item.remaining_quantity
        if remaining > 0:
            _restock(item, remaining)
            item.quantity_cancelled = item.quantity
            item.save(update_fields=["quantity_cancelled"])

    transition_order_status(order, Order.STATUS_CANCELLED, actor=actor, note=note)
    return order


def cancel_order_items(order: Order, items_spec, *, actor=None, note: str = "") -> Order:
    """Partially or fully cancel order items.

    ``items_spec`` is a dict of ``{order_item_id: quantity_to_cancel}`` or a
    list of ids (cancelling each item's full remaining quantity).
    """
    OrderStateMachine.validate_transition(order.status, Order.STATUS_CANCELLED)

    if isinstance(items_spec, dict):
        pairs = list(items_spec.items())
    else:
        pairs = [(item_id, None) for item_id in items_spec]
    if not pairs:
        raise NotFoundError("No matching order items", code="orders.items_not_found")

    cancelled_amount = Decimal("0.0000")
    for item_id, quantity_to_cancel in pairs:
        item = OrderItem.objects.filter(order=order, pk=item_id).first()
        if item is None:
            raise NotFoundError("Order item not found", code="orders.item_not_found")
        remaining = item.remaining_quantity
        to_cancel = remaining if quantity_to_cancel is None else min(quantity_to_cancel, remaining)
        if to_cancel <= 0:
            continue
        _restock(item, to_cancel)
        item.quantity_cancelled += to_cancel
        item.save(update_fields=["quantity_cancelled"])
        cancelled_amount += item.unit_price * to_cancel

    _recalculate_totals(order, cancelled_amount)
    _log_status(
        order, status_type=OrderStatusLog.TYPE_ORDER, from_value=order.status,
        to_value=order.status, actor=actor, note=f"Partial cancel: {note}",
    )
    return order


def refundable_amount(order: Order) -> Decimal:
    refunded = order.refunds.aggregate(total=models_sum("amount"))["total"]
    return order.total - (refunded or Decimal("0.0000"))


def models_sum(field_name: str):
    from django.db.models import Sum
    from django.db.models.fields import DecimalField

    return Sum(field_name, output_field=DecimalField(max_digits=18, decimal_places=4))


def refund_order(order: Order, amount, *, actor=None, reason: str = "") -> Refund:
    if order.payment_status != Order.PAYMENT_PAID:
        raise ValidationError(
            "Only paid orders can be refunded", code="orders.not_refundable"
        )
    amount = Decimal(amount)
    if amount <= 0:
        raise ValidationError("Refund amount must be positive", code="orders.bad_refund_amount")

    refundable = refundable_amount(order)
    if amount > refundable:
        raise ValidationError(
            f"Refund amount exceeds refundable balance ({refundable})", code="orders.over_refund"
        )

    refund = Refund.objects.create(
        order=order, amount=amount, reason=reason, actor=actor
    )

    if amount == refundable:
        order.payment_status = Order.PAYMENT_REFUNDED
        order.save(update_fields=["payment_status"])
        _log_status(
            order, status_type=OrderStatusLog.TYPE_PAYMENT, from_value=Order.PAYMENT_PAID,
            to_value=Order.PAYMENT_REFUNDED, actor=actor, note=reason,
        )
        transition_order_status(order, Order.STATUS_REFUNDED, actor=actor, note=reason)
    return refund


def refund_order_item(order_item: OrderItem, quantity: int, *, actor=None, reason: str = "") -> Refund:
    if quantity <= 0 or quantity > order_item.remaining_quantity:
        raise ValidationError("Invalid refund quantity", code="orders.bad_refund_quantity")
    amount = (order_item.unit_price * quantity).quantize(Decimal("0.0001"))
    order = order_item.order
    if order.payment_status != Order.PAYMENT_PAID:
        raise ValidationError("Only paid orders can be refunded", code="orders.not_refundable")
    if amount > refundable_amount(order):
        raise ValidationError("Refund exceeds refundable balance", code="orders.over_refund")

    refund = Refund.objects.create(
        order=order, order_item=order_item, amount=amount, reason=reason, actor=actor
    )
    if refundable_amount(order) <= 0:
        order.payment_status = Order.PAYMENT_REFUNDED
        order.save(update_fields=["payment_status"])
    return refund


def request_return(order: Order, items, *, user=None, reason: str = "") -> ReturnRequest:
    if order.status not in (Order.STATUS_PAID, Order.STATUS_SHIPPED, Order.STATUS_COMPLETED):
        raise ValidationError(
            "Return is not allowed for this order status", code="orders.return_not_allowed"
        )
    if not items:
        raise ValidationError("Return requires at least one item", code="orders.return_empty")

    with transaction.atomic():
        return_request = ReturnRequest.objects.create(order=order, user=user, reason=reason)
        for order_item, quantity in items:
            if quantity <= 0 or quantity > order_item.remaining_quantity:
                raise ValidationError(
                    "Invalid return quantity", code="orders.bad_return_quantity"
                )
            ReturnRequestItem.objects.create(
                return_request=return_request, order_item=order_item, quantity=quantity
            )
    return return_request


def approve_return(return_request: ReturnRequest, *, actor=None) -> ReturnRequest:
    if return_request.status != ReturnRequest.STATUS_REQUESTED:
        raise ValidationError(
            "Only requested returns can be approved", code="orders.invalid_return_transition"
        )
    return_request.status = ReturnRequest.STATUS_APPROVED
    return_request.save(update_fields=["status"])
    return return_request


def reject_return(return_request: ReturnRequest, *, actor=None) -> ReturnRequest:
    if return_request.status != ReturnRequest.STATUS_REQUESTED:
        raise ValidationError(
            "Only requested returns can be rejected", code="orders.invalid_return_transition"
        )
    return_request.status = ReturnRequest.STATUS_REJECTED
    return_request.save(update_fields=["status"])
    return return_request


def receive_return(return_request: ReturnRequest, *, actor=None) -> ReturnRequest:
    if return_request.status != ReturnRequest.STATUS_APPROVED:
        raise ValidationError(
            "Only approved returns can be received", code="orders.invalid_return_transition"
        )
    for return_item in return_request.items.select_related("order_item"):
        _restock(return_item.order_item, return_item.quantity)
    return_request.status = ReturnRequest.STATUS_RECEIVED
    return_request.save(update_fields=["status"])
    return return_request


def add_order_note(order: Order, note: str, *, note_type: str = "internal", author=None) -> OrderNote:
    if not note or not note.strip():
        raise ValidationError("Note text is required", code="orders.note_required")
    if note_type not in (OrderNote.TYPE_INTERNAL, OrderNote.TYPE_CUSTOMER):
        raise ValidationError("Invalid note type", code="orders.invalid_note_type")
    return OrderNote.objects.create(order=order, note=note, note_type=note_type, author=author)


def order_notes(order: Order, *, include_internal: bool = True):
    queryset = order.notes.all()
    if not include_internal:
        queryset = queryset.filter(note_type=OrderNote.TYPE_CUSTOMER)
    return queryset


def issue_invoice(order: Order, *, actor=None) -> Order:
    if order.invoice_number:
        raise ConflictError("Invoice already issued", code="orders.invoice_exists")
    order.invoice_number = f"INV-{uuid.uuid4().hex[:10].upper()}"
    order.invoice_date = timezone.now()
    order.save(update_fields=["invoice_number", "invoice_date"])
    return order
