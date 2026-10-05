from unittest.mock import patch

import pytest

pytestmark = [pytest.mark.django_db]


def test_health_all_ok(api_client):
    with patch("core.health.checks.check_redis", return_value="ok"):
        response = api_client.get("/health/")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "checks": {"application": "ok", "database": "ok", "redis": "ok"},
    }


def test_health_degraded_when_redis_down(api_client):
    with patch("core.health.checks.check_redis", side_effect=RuntimeError("down")):
        response = api_client.get("/health/")

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "degraded"
    assert body["checks"]["redis"] == "error"


def test_health_degraded_when_db_down(api_client):
    with patch("core.health.checks.check_database", side_effect=RuntimeError("down")):
        response = api_client.get("/health/")

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "degraded"
    assert body["checks"]["database"] == "error"


def test_health_only_get_allowed(api_client):
    response = api_client.post("/health/")
    assert response.status_code == 405
