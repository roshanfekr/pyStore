import redis as redis_client
from django.conf import settings
from django.db import connection


def check_application() -> str:
    return "ok"


def check_database() -> str:
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        cursor.fetchone()
    return "ok"


def check_redis() -> str:
    client = redis_client.Redis.from_url(
        settings.REDIS_URL, socket_connect_timeout=2, socket_timeout=2
    )
    if not client.ping():
        raise RuntimeError("Redis PING failed")
    return "ok"


def run_health_checks() -> dict:
    checks = {
        "application": check_application,
        "database": check_database,
        "redis": check_redis,
    }

    results = {}
    for name, check in checks.items():
        try:
            results[name] = check()
        except Exception:
            results[name] = "error"
    return results
