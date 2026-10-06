import pytest
from django.contrib.auth import get_user_model

from apps.notifications.settings_defs import NAMESPACE
from core.settings.service import settings_service

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(email="notify@example.com", password="Str0ng!Passw0rd")


@pytest.fixture
def store(db):
    from apps.stores.services import create_store

    return create_store("Notify Store")


@pytest.fixture
def sync_delivery(db):
    """Disable async delivery so on_commit queueing sends immediately."""
    previous = settings_service.get(NAMESPACE, "async_delivery")
    settings_service.set(NAMESPACE, "async_delivery", False)
    yield
    settings_service.set(NAMESPACE, "async_delivery", previous)


def set_notification_setting(key: str, value) -> None:
    settings_service.set(NAMESPACE, key, value)
