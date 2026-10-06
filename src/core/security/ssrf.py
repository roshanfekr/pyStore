"""SSRF protection for user-supplied outbound URLs (webhooks, etc.)."""

import ipaddress
import socket
from urllib.parse import urlparse

from core.exceptions import ValidationError

ALLOWED_SCHEMES = ("http", "https")


def _is_private_ip(ip: str) -> bool:
    """True only for IP literals; hostnames are checked via DNS separately."""
    try:
        parsed = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return (
        parsed.is_private
        or parsed.is_loopback
        or parsed.is_link_local
        or parsed.is_multicast
        or parsed.is_reserved
        or parsed.is_unspecified
    )


def _hostname_addresses(hostname: str) -> list[str]:
    try:
        infos = socket.getaddrinfo(hostname, None)
    except (socket.gaierror, OSError):
        return []
    return [info[4][0] for info in infos]


def validate_public_url(url: str, *, allow_private: bool = False) -> None:
    """Reject URLs that do not point at a public host.

    Guards webhook targets and similar staff/user-supplied URLs against
    SSRF towards the internal network. DNS is resolved so hostnames that
    resolve to private space are rejected too.
    """
    if not url or not str(url).strip():
        raise ValidationError("URL is required", code="security.url_required")

    parsed = urlparse(str(url))
    if parsed.scheme.lower() not in ALLOWED_SCHEMES:
        raise ValidationError("Only http and https URLs are allowed", code="security.url_scheme")
    if not parsed.hostname:
        raise ValidationError("URL must include a host", code="security.url_host")

    if allow_private:
        return

    if _is_private_ip(parsed.hostname):
        raise ValidationError(
            "URLs pointing at private or local addresses are not allowed",
            code="security.url_private",
        )

    for address in _hostname_addresses(parsed.hostname):
        if _is_private_ip(address):
            raise ValidationError(
                "URL host resolves to a private or local address",
                code="security.url_private",
            )
