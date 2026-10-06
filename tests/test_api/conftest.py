import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.identity.services.roles import ensure_permission, ensure_role, grant_role

User = get_user_model()

PASSWORD = "Str0ng!Passw0rd"


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user(db):
    return User.objects.create_user(email="apiuser@example.com", password=PASSWORD)


@pytest.fixture
def auth_client(api_client, user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def grant_permission(user, codename: str):
    permission, _ = ensure_permission(codename, display_name=codename)
    role = ensure_role(f"Role for {codename}")
    role.permissions.add(permission)
    grant_role(user, role.name)
