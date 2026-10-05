import pytest
from django.conf import settings as django_settings

from core.settings import SettingsError, settings_service
from core.settings.crypto import decrypt_value, encrypt_value, is_encrypted
from core.settings.models import Setting
from core.settings.service import SettingsService

pytestmark = [pytest.mark.django_db]


@pytest.fixture
def service():
    service = SettingsService()
    service.register("global", "site_name", default="pyStore", value_type=str)
    service.register("global", "items_per_page", default=20, value_type=int)
    service.register("global", "maintenance", default=False, value_type=bool)
    service.register("global", "api_key", default="", value_type=str, sensitive=True)
    service.register("store:default", "currency", default="USD", value_type=str)
    return service


def test_registered_setting_returns_default(service):
    assert settings_service.get("global", "site_name") == "pyStore"
    assert service.get("global", "items_per_page") == 20


def test_set_and_get_persists(service):
    service.set("global", "site_name", "My Shop")
    assert service.get("global", "site_name") == "My Shop"
    assert Setting.objects.get(namespace="global", key="site_name").value == "My Shop"


def test_type_validation(service):
    with pytest.raises(SettingsError):
        service.set("global", "items_per_page", "twenty")
    with pytest.raises(SettingsError):
        service.set("global", "maintenance", 1)
    with pytest.raises(SettingsError):
        service.set("global", "site_name", 42)


def test_bool_is_not_accepted_as_int(service):
    service.register("global", "count", default=0, value_type=int)
    with pytest.raises(SettingsError):
        service.set("global", "count", True)


def test_unregistered_setting_without_row_raises(service):
    with pytest.raises(SettingsError):
        service.get("global", "missing_key")


def test_untyped_setting_accepts_any_json(service):
    service.register("global", "custom")
    service.set("global", "custom", {"any": ["json"]})
    assert service.get("global", "custom") == {"any": ["json"]}


def test_sensitive_value_is_encrypted_at_rest(service):
    service.set("global", "api_key", "super-secret-key")
    row = Setting.objects.get(namespace="global", key="api_key")
    assert is_encrypted(row.value)
    assert "super-secret-key" not in row.value
    assert service.get("global", "api_key") == "super-secret-key"


def test_sensitive_values_masked_in_all(service):
    service.set("global", "api_key", "super-secret-key")
    listing = service.all("global")
    assert listing["api_key"] == "******"
    assert listing["site_name"] == "pyStore"


def test_sensitive_decryption_with_wrong_key_fails(service, monkeypatch):
    from django.conf import settings as dj

    service.set("global", "api_key", "super-secret-key")
    monkeypatch.setattr(dj, "SETTINGS_ENCRYPTION_KEY", "another-key", raising=False)
    settings_service.clear_cache()
    with pytest.raises(SettingsError):
        service.get("global", "api_key")


def test_namespaces_are_isolated(service):
    service.set("store:default", "currency", "EUR")
    service.set("plugin:sample_plugin", "greeting", "Salam")

    assert service.get("store:default", "currency") == "EUR"
    assert service.get("plugin:sample_plugin", "greeting") == "Salam"
    assert service.all("store:default") == {"currency": "EUR"}
    assert service.all("plugin:sample_plugin") == {"greeting": "Salam"}


def test_store_and_plugin_conventions_usable(service):
    service.set("plugin:sample_plugin", "target", "World")
    assert service.get("plugin:sample_plugin", "target") == "World"


def test_delete_removes_setting(service):
    service.set("global", "site_name", "changed")
    service.delete("global", "site_name")
    assert service.get("global", "site_name") == "pyStore"


def test_service_cache_invalidation(service):
    service.set("global", "site_name", "first")
    service.set("global", "site_name", "second")
    assert service.get("global", "site_name") == "second"


def test_crypto_round_trip():
    token = encrypt_value("plain-text")
    assert token != "plain-text"
    assert decrypt_value(token) == "plain-text"


def test_encryption_key_from_env_overrides_secret(service, monkeypatch, db):
    from django.conf import settings as dj

    monkeypatch.setattr(dj, "SETTINGS_ENCRYPTION_KEY", "custom-key", raising=False)
    service.set("global", "api_key", "secret")
    assert service.get("global", "api_key") == "secret"


def test_django_settings_untouched_by_settings_service(service):
    service.set("global", "site_name", "new-name")
    assert not hasattr(django_settings, "site_name")
