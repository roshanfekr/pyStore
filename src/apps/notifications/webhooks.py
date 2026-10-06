import hashlib
import hmac
import json
import logging
import time
import urllib.error
import urllib.request

from django.conf import settings
from django.utils import timezone

from apps.notifications.models import WebhookDeliveryLog, WebhookEndpoint
from core.exceptions import NotFoundError
from core.security.ssrf import validate_public_url

logger = logging.getLogger(__name__)

WEBHOOK_SIGNATURE_HEADER = "X-Webhook-Signature"
WEBHOOK_EVENT_HEADER = "X-Webhook-Event"


def sign_payload(body: bytes, secret: str) -> str:
    """HMAC-SHA256 hex signature of the raw payload body."""
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


def build_webhook_payload(event_name: str, context: dict) -> dict:
    return {
        "event_name": event_name,
        "context": context if isinstance(context, dict) else {},
        "sent_at": timezone.now().isoformat(),
    }


def deliver_webhook(
    endpoint: WebhookEndpoint, event_name: str, payload: dict, *, attempt: int = 1
) -> WebhookDeliveryLog:
    """Perform one signed delivery attempt and record it in the delivery log."""
    started = time.monotonic()
    status_code = None
    error = ""
    successful = False
    body = b""
    try:
        validate_public_url(
            endpoint.target_url,
            allow_private=getattr(settings, "SECURITY_ALLOW_PRIVATE_URLS", False),
        )
        body = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            WEBHOOK_EVENT_HEADER: event_name,
        }
        if endpoint.secret:
            headers[WEBHOOK_SIGNATURE_HEADER] = sign_payload(body, endpoint.secret)

        request = urllib.request.Request(
            endpoint.target_url, data=body, headers=headers, method="POST"
        )
        with urllib.request.urlopen(request, timeout=10) as response:
            status_code = response.status
        successful = 200 <= status_code < 300
        if not successful:
            error = f"Unexpected HTTP status {status_code}"
    except urllib.error.HTTPError as exc:
        status_code = exc.code
        error = f"HTTP {exc.code}"
    except Exception as exc:
        logger.warning("Webhook delivery to %s failed: %s", endpoint.target_url, exc)
        error = str(exc)
    duration_ms = int((time.monotonic() - started) * 1000)

    return WebhookDeliveryLog.objects.create(
        endpoint=endpoint,
        event_name=event_name,
        attempt=attempt,
        successful=successful,
        status_code=status_code,
        error=error,
        duration_ms=duration_ms,
    )


def deliver_webhook_with_retry(
    endpoint_id: str, event_name: str, payload: dict, attempt: int = 1
) -> bool:
    """Deliver a webhook once and schedule celery retries on failure."""
    from apps.notifications.tasks import retry_webhook_delivery_task

    endpoint = WebhookEndpoint.objects.filter(pk=endpoint_id, is_active=True).first()
    if endpoint is None:
        raise NotFoundError("Webhook endpoint not found", code="notifications.endpoint_not_found")

    log = deliver_webhook(endpoint, event_name, payload, attempt=attempt)
    if log.successful:
        return True

    if attempt <= endpoint.max_retries:
        retry_webhook_delivery_task.apply_async(
            args=[str(endpoint_id), event_name, payload, attempt + 1],
            countdown=min(30 * (2**attempt), 3600),
        )
    return False
