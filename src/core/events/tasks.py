import logging

from celery import shared_task

from core.events.dispatcher import dispatcher
from core.events.registry import event_registry

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def dispatch_event_task(self, event_name: str, payload: dict):
    event_class = event_registry.get(event_name)
    if event_class is None:
        logger.error("Cannot dispatch unknown event %r", event_name)
        return None
    try:
        event = event_class.from_payload(payload)
    except Exception:
        logger.exception("Failed to rebuild event %r from payload", event_name)
        raise self.retry(exc=True) from None
    dispatcher.dispatch(event)
    return True
