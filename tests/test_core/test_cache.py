import pytest

from core.cache import CacheService

pytestmark = [pytest.mark.django_db]


@pytest.fixture
def cache_store():
    from django.core.cache import cache

    cache.clear()
    return CacheService(namespace="test_ns")


def test_set_and_get(cache_store):
    cache_store.set("product:1", {"id": 1})
    assert cache_store.get("product:1") == {"id": 1}


def test_get_default_when_missing(cache_store):
    assert cache_store.get("missing") is None
    assert cache_store.get("missing", "fallback") == "fallback"


def test_delete(cache_store):
    cache_store.set("key", "value")
    cache_store.delete("key")
    assert cache_store.get("key") is None


def test_get_or_set_calls_factory_once(cache_store):
    calls = []

    def factory():
        calls.append(1)
        return "computed"

    assert cache_store.get_or_set("k", factory) == "computed"
    assert cache_store.get_or_set("k", factory) == "computed"
    assert len(calls) == 1


def test_clear_namespace_invalidates_all_keys(cache_store):
    cache_store.set("a", 1)
    cache_store.set("b", 2)
    cache_store.clear_namespace()
    assert cache_store.get("a") is None
    assert cache_store.get("b") is None


def test_namespaces_are_isolated(cache_store):
    other = CacheService(namespace="other_ns")
    cache_store.set("shared-key", "from-test-ns")
    other.set("shared-key", "from-other-ns")
    assert cache_store.get("shared-key") == "from-test-ns"
    assert other.get("shared-key") == "from-other-ns"

    cache_store.clear_namespace()
    assert cache_store.get("shared-key") is None
    assert other.get("shared-key") == "from-other-ns"


def test_custom_backend_injection():
    from django.core.cache.backends.locmem import LocMemCache

    backend = LocMemCache("unique-backend", {})
    service = CacheService(backend=backend, namespace="injected")
    service.set("x", 5)
    assert service.get("x") == 5
