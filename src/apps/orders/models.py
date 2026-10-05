import uuid

from django.conf import settings
from django.db import models

from core.models import BaseModel


def generate_order_number() -> str:
    return f"ORD-{uuid.uuid4().hex[:12].upper()}"


class Order(BaseModel):
    STATUS_PENDING = "pending"
    STATUS_PROCESSING = "processing"
    STATUS_PAID = "paid"
    STATUS_SHIPPED = "shipped"
    STATUS_COMPLETED = "completed"
    STATUS_CANCELLED = "cancelled"
    STATUS_REFUNDED = "refunded"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_PROCESSING, "Processing"),
        (STATUS_PAID, "Paid"),
        (STATUS_SHIPPED, "Shipped"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_CANCELLED, "Cancelled"),
        (STATUS_REFUNDED, "Refunded"),
    ]

    PAYMENT_PENDING = "pending"
    PAYMENT_PAID = "paid"
    PAYMENT_FAILED = "failed"
    PAYMENT_REFUNDED = "refunded"
    PAYMENT_STATUS_CHOICES = [
        (PAYMENT_PENDING, "Pending"),
        (PAYMENT_PAID, "Paid"),
        (PAYMENT_FAILED, "Failed"),
        (PAYMENT_REFUNDED, "Refunded"),
    ]

    SHIPMENT_NOT_SHIPPED = "not_shipped"
    SHIPMENT_SHIPPED = "shipped"
    SHIPMENT_DELIVERED = "delivered"
    SHIPMENT_STATUS_CHOICES = [
        (SHIPMENT_NOT_SHIPPED, "Not shipped"),
        (SHIPMENT_SHIPPED, "Shipped"),
        (SHIPMENT_DELIVERED, "Delivered"),
    ]

    number = models.CharField(max_length=30, unique=True, default=generate_order_number)
    store = models.ForeignKey("stores.Store", related_name="orders", on_delete=models.PROTECT)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, related_name="orders", on_delete=models.SET_NULL
    )
    email = models.CharField(max_length=254)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_PENDING)
    payment_status = models.CharField(
        max_length=16, choices=PAYMENT_STATUS_CHOICES, default=PAYMENT_PENDING
    )
    shipment_status = models.CharField(
        max_length=16, choices=SHIPMENT_STATUS_CHOICES, default=SHIPMENT_NOT_SHIPPED
    )

    subtotal = models.DecimalField(max_digits=18, decimal_places=4, default=0)
    discount_amount = models.DecimalField(max_digits=18, decimal_places=4, default=0)
    shipping_amount = models.DecimalField(max_digits=18, decimal_places=4, default=0)
    tax_amount = models.DecimalField(max_digits=18, decimal_places=4, default=0)
    total = models.DecimalField(max_digits=18, decimal_places=4, default=0)
    currency = models.CharField(max_length=10, default="USD")

    coupon_code = models.CharField(max_length=50, blank=True)
    shipping_method = models.CharField(max_length=50, blank=True)
    payment_method = models.CharField(max_length=50, blank=True)

    invoice_number = models.CharField(max_length=50, unique=True, null=True, blank=True)
    invoice_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Order"
        verbose_name_plural = "Orders"
        ordering = ["-created_at"]

    def __str__(self):
        return self.number


class OrderItem(BaseModel):
    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey(
        "catalog.Product", null=True, blank=True, related_name="order_items", on_delete=models.SET_NULL
    )
    variant = models.ForeignKey(
        "catalog.ProductVariant", null=True, blank=True, related_name="order_items",
        on_delete=models.SET_NULL,
    )
    product_name = models.CharField(max_length=300)
    sku = models.CharField(max_length=100, blank=True)
    quantity = models.PositiveIntegerField()
    quantity_cancelled = models.PositiveIntegerField(default=0)
    unit_price = models.DecimalField(max_digits=18, decimal_places=4)
    line_total = models.DecimalField(max_digits=18, decimal_places=4)

    class Meta:
        verbose_name = "Order item"
        verbose_name_plural = "Order items"

    def __str__(self):
        return f"{self.product_name} x{self.quantity}"

    @property
    def remaining_quantity(self) -> int:
        return self.quantity - self.quantity_cancelled


class OrderAddress(BaseModel):
    TYPE_SHIPPING = "shipping"
    TYPE_BILLING = "billing"
    TYPE_CHOICES = [(TYPE_SHIPPING, "Shipping"), (TYPE_BILLING, "Billing")]

    order = models.ForeignKey(Order, related_name="addresses", on_delete=models.CASCADE)
    address_type = models.CharField(max_length=10, choices=TYPE_CHOICES, default=TYPE_SHIPPING)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    email = models.CharField(max_length=254, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    country = models.CharField(max_length=2)
    state = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=30, blank=True)
    address_line = models.CharField(max_length=300)

    class Meta:
        verbose_name = "Order address"
        verbose_name_plural = "Order addresses"

    def __str__(self):
        return f"{self.order.number} ({self.address_type})"


class OrderStatusLog(models.Model):
    TYPE_ORDER = "order"
    TYPE_PAYMENT = "payment"
    TYPE_SHIPMENT = "shipment"
    TYPE_CHOICES = [(TYPE_ORDER, "Order"), (TYPE_PAYMENT, "Payment"), (TYPE_SHIPMENT, "Shipment")]

    order = models.ForeignKey(Order, related_name="status_logs", on_delete=models.CASCADE)
    status_type = models.CharField(max_length=10, choices=TYPE_CHOICES, default=TYPE_ORDER)
    from_value = models.CharField(max_length=20, blank=True)
    to_value = models.CharField(max_length=20)
    note = models.CharField(max_length=500, blank=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, related_name="order_status_logs",
        on_delete=models.SET_NULL,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Order status log"
        verbose_name_plural = "Order status logs"
        ordering = ["created_at"]


class OrderNote(models.Model):
    TYPE_INTERNAL = "internal"
    TYPE_CUSTOMER = "customer"
    TYPE_CHOICES = [(TYPE_INTERNAL, "Internal"), (TYPE_CUSTOMER, "Customer")]

    order = models.ForeignKey(Order, related_name="notes", on_delete=models.CASCADE)
    note_type = models.CharField(max_length=10, choices=TYPE_CHOICES, default=TYPE_INTERNAL)
    note = models.TextField()
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, related_name="order_notes",
        on_delete=models.SET_NULL,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Order note"
        verbose_name_plural = "Order notes"
        ordering = ["created_at"]

    def __str__(self):
        return f"Note on {self.order.number}"


class Refund(BaseModel):
    order = models.ForeignKey(Order, related_name="refunds", on_delete=models.PROTECT)
    order_item = models.ForeignKey(
        OrderItem, null=True, blank=True, related_name="refunds", on_delete=models.SET_NULL
    )
    amount = models.DecimalField(max_digits=18, decimal_places=4)
    reason = models.CharField(max_length=500, blank=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, related_name="refunds",
        on_delete=models.SET_NULL,
    )

    class Meta:
        verbose_name = "Refund"
        verbose_name_plural = "Refunds"

    def __str__(self):
        return f"Refund {self.amount} on {self.order.number}"


class ReturnRequest(BaseModel):
    STATUS_REQUESTED = "requested"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"
    STATUS_RECEIVED = "received"
    STATUS_CHOICES = [
        (STATUS_REQUESTED, "Requested"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_REJECTED, "Rejected"),
        (STATUS_RECEIVED, "Received"),
    ]

    order = models.ForeignKey(Order, related_name="return_requests", on_delete=models.PROTECT)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, related_name="return_requests",
        on_delete=models.SET_NULL,
    )
    reason = models.CharField(max_length=500)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_REQUESTED)

    class Meta:
        verbose_name = "Return request"
        verbose_name_plural = "Return requests"

    def __str__(self):
        return f"Return on {self.order.number}"


class ReturnRequestItem(models.Model):
    return_request = models.ForeignKey(
        ReturnRequest, related_name="items", on_delete=models.CASCADE
    )
    order_item = models.ForeignKey(OrderItem, related_name="return_items", on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
