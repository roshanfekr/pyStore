import pytest

from apps.stores.models import Store
from apps.stores.services import (
    add_store_domain,
    create_store,
    ensure_default_store,
    get_store_by_domain,
    get_store_setting,
    set_primary_store,
    set_store_localization,
    set_store_setting,
    set_store_status,
)
from core.exceptions import ConflictError, NotFoundError, ValidationError

pytestmark = [pytest.mark.django_db]


def test_create_store_with_domains():
    store = create_store("Shop One", domains=["shop1.example.com", "shopone.ir"])

    assert Store.objects.filter(slug="shop-one").exists()
    assert store.domains.count() == 2
    assert store.default_language == "en"
    assert store.supported_languages == ["en"]
    assert store.default_currency == "USD"


def test_create_store_requires_name():
    with pytest.raises(ValidationError):
        create_store("   ")


def test_store_slug_is_unique():
    create_store("Same Name")
    second = create_store("Same Name")
    assert second.slug == "same-name-2"


def test_ensure_default_store_is_idempotent():
    first = ensure_default_store()
    second = ensure_default_store()
    assert first.id == second.id
    assert Store.objects.filter(is_default=True).count() == 1


def test_set_primary_store_moves_flag():
    first = ensure_default_store()
    second = create_store("Second Store")

    set_primary_store(second)

    first.refresh_from_db()
    second.refresh_from_db()
    assert first.is_default is False
    assert second.is_default is True


def test_add_store_domain_validates():
    store = create_store("Domain Test")
    with pytest.raises(ValidationError):
        add_store_domain(store, "not-a-domain")
    with pytest.raises(ValidationError):
        add_store_domain(store, "")


def test_domain_cannot_be_reused():
    create_store("A", domains=["shared.example.com"])
    other = create_store("B")
    with pytest.raises(ConflictError):
        add_store_domain(other, "shared.example.com")


def test_domain_normalization_and_primary_flag():
    store = create_store("Normalize")
    domain = add_store_domain(store, "  NORMALIZE.Example.COM  ")
    assert domain.domain == "normalize.example.com"

    primary = add_store_domain(store, "primary.example.com", ssl_enabled=False, is_primary=True)
    assert primary.is_primary is True

    domain.refresh_from_db()
    assert domain.is_primary is False


def test_get_store_by_domain():
    store_a = create_store("Alpha", domains=["alpha.example.com"])
    create_store("Beta", domains=["beta.example.com"])

    found = get_store_by_domain("Alpha.Example.Com")
    assert found.id == store_a.id

    with pytest.raises(NotFoundError):
        get_store_by_domain("missing.example.com")


def test_store_localization_update():
    store = create_store("Locale")
    set_store_localization(
        store,
        default_language="fa",
        supported_languages=["fa", "en"],
        default_currency="IRR",
        supported_currencies=["IRR", "USD"],
        timezone_str="Asia/Tehran",
    )
    store.refresh_from_db()
    assert store.default_language == "fa"
    assert store.supported_languages == ["fa", "en"]
    assert store.default_currency == "IRR"
    assert store.timezone == "Asia/Tehran"


def test_store_status_toggle():
    store = create_store("Status")
    set_store_status(store, False)
    store.refresh_from_db()
    assert store.is_active is False


def test_store_soft_delete():
    store = create_store("Delete Me")
    store.delete()
    assert Store.objects.filter(pk=store.pk).exists() is False
    assert Store.all_objects.filter(pk=store.pk).exists()


def test_store_settings_via_settings_service():
    store = create_store("Settings Store")
    assert get_store_setting(store, "banner_text") is None

    set_store_setting(store, "banner_text", "Welcome!")
    assert get_store_setting(store, "banner_text") == "Welcome!"


def test_store_settings_are_isolated_per_store():
    store_a = create_store("Settings A")
    store_b = create_store("Settings B")

    set_store_setting(store_a, "banner_text", "Store A banner")

    assert get_store_setting(store_a, "banner_text") == "Store A banner"
    assert get_store_setting(store_b, "banner_text") is None


def test_multi_store_domains_resolution():
    store_a = create_store("Multi A", domains=["a.example.com"])
    store_b = create_store("Multi B", domains=["b.example.com"])

    assert get_store_by_domain("a.example.com").id == store_a.id
    assert get_store_by_domain("b.example.com").id == store_b.id
