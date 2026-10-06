import pytest
from django.test import override_settings

pytestmark = [pytest.mark.django_db]


def test_security_headers_on_api_response(api_client, db):
    response = api_client.get("/health/")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert "Content-Security-Policy" in response.headers
    assert response.headers["X-Frame-Options"] == "DENY"


def test_cors_header_not_sent_without_config(api_client, db):
    response = api_client.get("/health/", HTTP_ORIGIN="https://evil.example")
    assert "Access-Control-Allow-Origin" not in response.headers


@override_settings(CORS_ALLOWED_ORIGINS=["https://allowed.example"])
def test_cors_header_sent_for_allowed_origin(api_client, db):
    response = api_client.get("/health/", HTTP_ORIGIN="https://allowed.example")
    assert response.headers["Access-Control-Allow-Origin"] == "https://allowed.example"


@override_settings(CORS_ALLOWED_ORIGINS=["https://allowed.example"])
def test_cors_header_not_sent_for_disallowed_origin(api_client, db):
    response = api_client.get("/health/", HTTP_ORIGIN="https://evil.example")
    assert "Access-Control-Allow-Origin" not in response.headers


@override_settings(CORS_ALLOWED_ORIGINS=["https://allowed.example"])
def test_cors_preflight_returns_204(api_client, db):
    response = api_client.options(
        "/api/v1/products",
        HTTP_ORIGIN="https://allowed.example",
        HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
    )
    assert response.status_code == 204
    assert "POST" in response.headers["Access-Control-Allow-Methods"]


def test_preflight_without_allowed_origin_has_no_cors_headers(api_client, db):
    response = api_client.options("/api/v1/products", HTTP_ORIGIN="https://evil.example")
    assert "Access-Control-Allow-Methods" not in response.headers


def test_production_settings_enable_hardening(db):
    from unittest import mock

    with mock.patch.dict("os.environ", {"SECRET_KEY": "x"}):
        import importlib

        import config.settings.production as production

        importlib.reload(production)

    assert production.SECURE_SSL_REDIRECT is True
    assert production.SESSION_COOKIE_SECURE is True
    assert production.CSRF_COOKIE_SECURE is True
    assert production.SECURE_HSTS_SECONDS >= 31536000
    assert production.X_FRAME_OPTIONS == "DENY"
