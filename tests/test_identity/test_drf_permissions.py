import pytest
from rest_framework.test import APIRequestFactory

from apps.identity.api import has_perm
from apps.identity.models import User
from apps.identity.services.roles import ensure_permission, ensure_role, grant_role

pytestmark = [pytest.mark.django_db]

factory = APIRequestFactory()


@pytest.fixture
def user_with_perm(db):
    user = User.objects.create_user(email="drf@example.com", password="Str0ng!Passw0rd")
    perm = ensure_permission("order.view", display_name="View orders")[0]
    role = ensure_role("Order Viewers")
    role.permissions.add(perm)
    grant_role(user, "Order Viewers")
    return user


def test_has_perm_allows_authorized_user(user_with_perm):
    request = factory.get("/")
    request.user = user_with_perm

    assert has_perm("order.view")().has_permission(request, None) is True


def test_has_perm_denies_unauthorized_user(db):
    user = User.objects.create_user(email="plain@example.com", password="Str0ng!Passw0rd")
    request = factory.get("/")
    request.user = user

    assert has_perm("order.view")().has_permission(request, None) is False


def test_has_perm_denies_anonymous(db):
    from django.contrib.auth.models import AnonymousUser

    request = factory.get("/")
    request.user = AnonymousUser()

    assert has_perm("order.view")().has_permission(request, None) is False


def test_has_perm_denies_unauthenticated_request(db):
    from rest_framework.exceptions import NotAuthenticated  # noqa: F401

    request = factory.get("/")
    from django.contrib.auth.models import AnonymousUser

    request.user = AnonymousUser()
    assert has_perm("order.refund")().has_permission(request, None) is False
