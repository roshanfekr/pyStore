import pytest

from core.exceptions import ValidationError
from core.security.ssrf import validate_public_url


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/admin",
        "http://10.0.0.5/internal",
        "http://192.168.1.10/router",
        "http://172.16.0.9/host",
        "http://169.254.169.254/latest/meta-data",
        "http://[::1]/x",
        "http://0.0.0.0/x",
    ],
)
def test_private_ip_literals_are_blocked(url, db):
    with pytest.raises(ValidationError):
        validate_public_url(url)


@pytest.mark.parametrize("url", ["ftp://example.com/x", "file:///etc/passwd", "", None])
def test_invalid_schemes_are_rejected(url, db):
    with pytest.raises(ValidationError):
        validate_public_url(url)


def test_public_hostname_allowed_without_dns(db):
    # Unresolvable public hostnames fail open on DNS and pass validation.
    validate_public_url("https://hooks.example.com/target")


def test_hostname_resolving_to_private_ip_blocked(db, monkeypatch):
    from core.security import ssrf

    monkeypatch.setattr(
        ssrf, "_hostname_addresses", lambda host: ["10.0.0.1"]
    )
    with pytest.raises(ValidationError):
        validate_public_url("https://internal-rebind.example/x")


def test_allow_private_flag_bypasses_check(db):
    validate_public_url("http://127.0.0.1:8080/dev", allow_private=True)


def test_missing_host_rejected(db):
    with pytest.raises(ValidationError):
        validate_public_url("http://")
