from datetime import timezone as dt_timezone

from core.utils import get_client_ip, is_blank, normalize_whitespace, utc_now


def test_utc_now_is_timezone_aware():
    now = utc_now()
    assert now.tzinfo is not None
    assert now.tzinfo.utcoffset(now) == dt_timezone.utc.utcoffset(None)


def test_get_client_ip_prefers_forwarded_for():
    request = type("R", (), {"META": {"HTTP_X_FORWARDED_FOR": "1.1.1.1, 2.2.2.2", "REMOTE_ADDR": "3.3.3.3"}})()
    assert get_client_ip(request) == "1.1.1.1"


def test_get_client_ip_falls_back_to_remote_addr():
    request = type("R", (), {"META": {"REMOTE_ADDR": "3.3.3.3"}})()
    assert get_client_ip(request) == "3.3.3.3"


def test_get_client_ip_missing():
    request = type("R", (), {"META": {}})()
    assert get_client_ip(request) is None


def test_normalize_whitespace():
    assert normalize_whitespace("  a   b\tc  ") == "a b c"


def test_is_blank():
    assert is_blank(None) is True
    assert is_blank("   ") is True
    assert is_blank("x") is False
