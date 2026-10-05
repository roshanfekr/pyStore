import uuid
from datetime import timezone as dt_timezone

from core.events import DomainEvent, EventDispatcher, dispatcher, register_handler, subscribe


class OrderCreated(DomainEvent):
    pass


class PaymentCompleted(DomainEvent):
    pass


def test_event_has_id_name_and_utc_timestamp():
    event = OrderCreated()
    assert isinstance(event.event_id, str)
    uuid.UUID(event.event_id)
    assert event.event_name == "OrderCreated"
    assert event.occurred_at.tzinfo is not None
    assert event.occurred_at.tzinfo.utcoffset(event.occurred_at) == dt_timezone.utc.utcoffset(None)


def test_event_ids_are_unique():
    assert OrderCreated().event_id != OrderCreated().event_id


def test_subscribe_and_dispatch():
    bus = EventDispatcher()
    received = []
    bus.subscribe(OrderCreated, received.append)

    event = OrderCreated()
    bus.dispatch(event)

    assert received == [event]


def test_handlers_receive_only_their_event_type():
    bus = EventDispatcher()
    received = []
    bus.subscribe(OrderCreated, received.append)

    bus.dispatch(PaymentCompleted())

    assert received == []


def test_multiple_handlers_called_in_order():
    bus = EventDispatcher()
    calls = []
    bus.subscribe(OrderCreated, lambda e: calls.append("first"))
    bus.subscribe(OrderCreated, lambda e: calls.append("second"))

    bus.dispatch(OrderCreated())

    assert calls == ["first", "second"]


def test_handler_failure_is_isolated():
    bus = EventDispatcher()
    calls = []

    def broken(event):
        raise RuntimeError("handler bug")

    bus.subscribe(OrderCreated, broken)
    bus.subscribe(OrderCreated, lambda e: calls.append("ok"))

    bus.dispatch(OrderCreated())

    assert calls == ["ok"]


def test_unsubscribe():
    bus = EventDispatcher()
    calls = []
    handler = lambda e: calls.append(e)  # noqa: E731
    bus.subscribe(OrderCreated, handler)
    bus.unsubscribe(OrderCreated, handler)

    bus.dispatch(OrderCreated())

    assert calls == []


def test_dispatch_all():
    bus = EventDispatcher()
    received = []
    bus.subscribe(OrderCreated, received.append)
    bus.subscribe(PaymentCompleted, received.append)

    bus.dispatch_all([OrderCreated(), PaymentCompleted()])

    assert len(received) == 2


def test_global_subscribe_decorator():
    calls = []

    @subscribe(OrderCreated)
    def handle(event):
        calls.append(event)

    try:
        dispatcher.dispatch(OrderCreated())
    finally:
        dispatcher.unsubscribe(OrderCreated, handle)

    assert len(calls) == 1


def test_global_register_handler():
    calls = []
    handler = lambda e: calls.append(e)  # noqa: E731
    register_handler(PaymentCompleted, handler)

    try:
        dispatcher.dispatch(PaymentCompleted())
    finally:
        dispatcher.unsubscribe(PaymentCompleted, handler)

    assert len(calls) == 1
