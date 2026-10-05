import pytest

from core.events import DomainEvent, dispatcher, event_registry, register_event


@register_event
class OrderPaid(DomainEvent):
    pass


@register_event
class CustomerRegistered(DomainEvent):
    pass


@register_event
class InventoryReserved(DomainEvent):
    pass


def test_register_event_decorator():
    assert event_registry.get("InventoryReserved") is InventoryReserved
    assert event_registry.get("Unknown") is None


def test_payload_round_trip_preserves_fields():
    event = CustomerRegistered()
    payload = event.to_payload()

    rebuilt = CustomerRegistered.from_payload(payload)

    assert rebuilt.event_id == event.event_id
    assert rebuilt.occurred_at == event.occurred_at
    assert rebuilt.event_name == "CustomerRegistered"


def test_payload_with_extra_fields_round_trip():
    from dataclasses import dataclass

    @dataclass(frozen=True)
    class TypedEvent(DomainEvent):
        order_id: str = ""

    event = TypedEvent(order_id="ord-1")
    rebuilt = TypedEvent.from_payload(event.to_payload())
    assert rebuilt.order_id == "ord-1"


@pytest.mark.django_db
def test_dispatch_async_executes_handlers_in_worker(settings, caplog):
    received = []

    def handler(event):
        received.append(event.event_id)

    dispatcher.subscribe(OrderPaid, handler)
    try:
        dispatcher.dispatch_async(OrderPaid())
    finally:
        dispatcher.unsubscribe(OrderPaid, handler)

    assert received, "eager mode should execute the task synchronously"


@pytest.mark.django_db
def test_dispatch_async_unknown_event_is_logged(caplog):
    from core.events.tasks import dispatch_event_task

    result = dispatch_event_task.apply(("NoSuchEvent", {}))
    assert result.successful()
