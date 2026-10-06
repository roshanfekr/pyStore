import pytest
from rest_framework.test import APIClient


@pytest.fixture(autouse=True)
def _clear_shared_caches():
    """Singleton caches (settings, auth counters) must not leak between tests."""
    from django.core.cache import cache

    from core.settings.service import settings_service

    settings_service.clear_cache()
    cache.clear()
    yield
    settings_service.clear_cache()
    cache.clear()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def sync_delivery(db):
    """Disable async notification delivery so on_commit queueing sends now."""
    from core.settings.service import settings_service

    settings_service.set("notifications", "async_delivery", False)
    yield
    settings_service.set("notifications", "async_delivery", True)
