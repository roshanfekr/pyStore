from apps.notifications.models import NotificationTemplate

DEFAULT_TEMPLATES: list[dict] = [
    {
        "code": "customer_registered_email",
        "name": "Customer registered (email)",
        "event_name": "CustomerRegistered",
        "channel": NotificationTemplate.CHANNEL_EMAIL,
        "subject": "Welcome to {{ store_name }}",
        "body": (
            "Hi,\n\n"
            "Welcome to {{ store_name }}! Your account ({{ email }}) has been created.\n\n"
            "Kind regards,\n{{ store_name }} team"
        ),
    },
    {
        "code": "customer_registered_inapp",
        "name": "Customer registered (in-app)",
        "event_name": "CustomerRegistered",
        "channel": NotificationTemplate.CHANNEL_INAPP,
        "subject": "Welcome to {{ store_name }}",
        "body": "Your account ({{ email }}) has been created. Enjoy your visit!",
    },
    {
        "code": "password_reset_email",
        "name": "Password reset (email)",
        "event_name": "PasswordReset",
        "channel": NotificationTemplate.CHANNEL_EMAIL,
        "subject": "Your {{ store_name }} password was changed",
        "body": (
            "Hi,\n\n"
            "The password for {{ email }} was changed on {{ occurred_at }}.\n"
            "If this was not you, please contact support immediately.\n\n"
            "{{ store_name }} team"
        ),
    },
    {
        "code": "password_reset_inapp",
        "name": "Password reset (in-app)",
        "event_name": "PasswordReset",
        "channel": NotificationTemplate.CHANNEL_INAPP,
        "subject": "Your password was changed",
        "body": "The password for {{ email }} was changed on {{ occurred_at }}.",
    },
    {
        "code": "order_created_email",
        "name": "Order created (email)",
        "event_name": "OrderCreated",
        "channel": NotificationTemplate.CHANNEL_EMAIL,
        "subject": "Your order {{ order_number }} was received",
        "body": (
            "Hi,\n\n"
            "We received your order {{ order_number }} on {{ occurred_at }}.\n"
            "Order total: {{ total }} {{ currency }}\n\n"
            "{{ store_name }} team"
        ),
    },
    {
        "code": "order_created_inapp",
        "name": "Order created (in-app)",
        "event_name": "OrderCreated",
        "channel": NotificationTemplate.CHANNEL_INAPP,
        "subject": "Order {{ order_number }} placed",
        "body": "Your order {{ order_number }} ({{ total }} {{ currency }}) was received.",
    },
    {
        "code": "order_paid_email",
        "name": "Order paid (email)",
        "event_name": "OrderPaid",
        "channel": NotificationTemplate.CHANNEL_EMAIL,
        "subject": "Payment received for order {{ order_number }}",
        "body": (
            "Hi,\n\n"
            "We received the payment for order {{ order_number }} ({{ total }} {{ currency }}).\n\n"
            "{{ store_name }} team"
        ),
    },
    {
        "code": "order_paid_inapp",
        "name": "Order paid (in-app)",
        "event_name": "OrderPaid",
        "channel": NotificationTemplate.CHANNEL_INAPP,
        "subject": "Order {{ order_number }} paid",
        "body": "Payment for order {{ order_number }} was received.",
    },
    {
        "code": "order_shipped_email",
        "name": "Order shipped (email)",
        "event_name": "OrderShipped",
        "channel": NotificationTemplate.CHANNEL_EMAIL,
        "subject": "Order {{ order_number }} has shipped",
        "body": (
            "Hi,\n\n"
            "Your order {{ order_number }} has shipped on {{ occurred_at }}.\n\n"
            "{{ store_name }} team"
        ),
    },
    {
        "code": "order_shipped_inapp",
        "name": "Order shipped (in-app)",
        "event_name": "OrderShipped",
        "channel": NotificationTemplate.CHANNEL_INAPP,
        "subject": "Order {{ order_number }} shipped",
        "body": "Your order {{ order_number }} has shipped.",
    },
    {
        "code": "order_cancelled_email",
        "name": "Order cancelled (email)",
        "event_name": "OrderCancelled",
        "channel": NotificationTemplate.CHANNEL_EMAIL,
        "subject": "Order {{ order_number }} was cancelled",
        "body": (
            "Hi,\n\n"
            "Your order {{ order_number }} was cancelled on {{ occurred_at }}.\n"
            "If you have questions, contact support.\n\n"
            "{{ store_name }} team"
        ),
    },
    {
        "code": "order_cancelled_inapp",
        "name": "Order cancelled (in-app)",
        "event_name": "OrderCancelled",
        "channel": NotificationTemplate.CHANNEL_INAPP,
        "subject": "Order {{ order_number }} cancelled",
        "body": "Your order {{ order_number }} was cancelled.",
    },
]


def ensure_default_notification_templates() -> int:
    """Create any missing default templates. Returns the number created."""
    created = 0
    for spec in DEFAULT_TEMPLATES:
        _, was_created = NotificationTemplate.objects.get_or_create(
            code=spec["code"],
            defaults=dict(spec),
        )
        if was_created:
            created += 1
    return created
