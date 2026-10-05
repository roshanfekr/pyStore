from core.events import DomainEvent


class SamplePing(DomainEvent):
    pass


pings: list[str] = []


def on_ping(event: SamplePing) -> None:
    pings.append(event.event_id)
