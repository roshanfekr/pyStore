import datetime
import decimal
import logging
import uuid

from core.audit.models import AuditLog
from core.utils.ip import get_client_ip

logger = logging.getLogger(__name__)

SENSITIVE_KEYS = {"password", "secret", "token", "key", "authorization", "credential"}
SENSITIVE_MASK = "******"


def json_safe(value):
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [json_safe(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (datetime.datetime, datetime.date)):
        return value.isoformat()
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, decimal.Decimal):
        return str(value)
    return str(value)


def mask_sensitive(data):
    """Mask values whose keys look secret-bearing, recursively."""
    if not isinstance(data, dict):
        return data
    masked = {}
    for key, value in data.items():
        lowered = str(key).lower()
        if any(marker in lowered for marker in SENSITIVE_KEYS):
            masked[key] = SENSITIVE_MASK
        elif isinstance(value, dict):
            masked[key] = mask_sensitive(value)
        else:
            masked[key] = value
    return masked


def audit(
    action: str,
    resource: str,
    resource_id: str = "",
    *,
    actor=None,
    request=None,
    before=None,
    after=None,
) -> AuditLog | None:
    """Record a sensitive operation. Never raises: auditing must not break ops."""
    try:
        user = actor if actor is not None and getattr(actor, "is_authenticated", False) else None
        if user is None and request is not None:
            request_user = getattr(request, "user", None)
            if request_user is not None and getattr(request_user, "is_authenticated", False):
                user = request_user

        ip_address = None
        user_agent = ""
        if request is not None:
            try:
                ip_address = get_client_ip(request)
            except Exception:
                ip_address = None
            user_agent = (request.META.get("HTTP_USER_AGENT") or "")[:300]

        entry = AuditLog.objects.create(
            actor=user,
            actor_email=(getattr(user, "email", "") or "")[:254],
            action=action,
            resource=resource,
            resource_id=str(resource_id or "")[:100],
            before_data=json_safe(mask_sensitive(before)) if before is not None else None,
            after_data=json_safe(mask_sensitive(after)) if after is not None else {},
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return entry
    except Exception:
        logger.exception("Failed to write audit log for %s on %s", action, resource)
        return None
