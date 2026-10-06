import logging

from apps.identity.models import User
from apps.notifications.services import queue_notification

logger = logging.getLogger(__name__)


def _user_for(user_id: str):
    if not user_id:
        return None
    return User.objects.filter(pk=user_id).first()


def handle_customer_registered(event) -> None:
    user = _user_for(getattr(event, "user_id", ""))
    queue_notification(
        "CustomerRegistered",
        {"email": event.email, "user_id": getattr(event, "user_id", "")},
        user=user,
    )


def handle_password_reset(event) -> None:
    user = User.objects.filter(email__iexact=event.email).first()
    queue_notification("PasswordReset", {"email": event.email}, user=user)


def _handle_order_event(event_name: str, event) -> None:
    user = _user_for(getattr(event, "user_id", ""))
    queue_notification(
        event_name,
        {
            "order_id": getattr(event, "order_id", ""),
            "order_number": getattr(event, "order_number", ""),
            "email": getattr(event, "email", ""),
            "user_id": getattr(event, "user_id", ""),
            "total": getattr(event, "total", ""),
            "currency": getattr(event, "currency", ""),
        },
        user=user,
    )


def handle_order_created(event) -> None:
    _handle_order_event("OrderCreated", event)


def handle_order_paid(event) -> None:
    _handle_order_event("OrderPaid", event)


def handle_order_shipped(event) -> None:
    _handle_order_event("OrderShipped", event)


def handle_order_cancelled(event) -> None:
    _handle_order_event("OrderCancelled", event)
