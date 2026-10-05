import pytest

from apps.identity.backends import PermissionBackend, user_permission_codenames
from apps.identity.models import Permission, User
from apps.identity.services.roles import (
    ensure_permission,
    ensure_role,
    grant_role,
    revoke_role,
    sync_plugin_permissions,
)

pytestmark = [pytest.mark.django_db]

PERM = "catalog.product.view"


@pytest.fixture
def user(db):
    return User.objects.create_user(email="rbac@example.com", password="Str0ng!Passw0rd")


@pytest.fixture
def catalog_permission(db):
    return ensure_permission(PERM, display_name="View products")[0]


def test_ensure_role_is_idempotent(db):
    first = ensure_role("Editors", is_system=True)
    second = ensure_role("Editors", is_system=True)
    assert first.id == second.id
    assert first.is_system is True


def test_ensure_permission_is_idempotent(db, catalog_permission):
    again, created = ensure_permission(PERM)
    assert again.id == catalog_permission.id
    assert created is False


def test_grant_and_revoke_role(user, db):
    ensure_role("Managers")
    grant_role(user, "Managers")
    assert user.roles.filter(name="Managers").exists()

    revoke_role(user, "Managers")
    assert user.roles.filter(name="Managers").exists() is False


def test_grant_missing_role_raises(user, db):
    from core.exceptions import NotFoundError

    with pytest.raises(NotFoundError):
        grant_role(user, "Nope")


def test_user_with_role_has_permission(user, catalog_permission, db):
    role = ensure_role("Catalog Viewers")
    role.permissions.add(catalog_permission)
    grant_role(user, "Catalog Viewers")

    assert user.has_perm(PERM) is True
    assert user.has_perm("catalog.product.delete") is False
    assert user_permission_codenames(user) == {PERM}


def test_user_without_role_has_no_permission(user, catalog_permission, db):
    assert user.has_perm(PERM) is False
    assert user_permission_codenames(user) == set()


def test_superuser_has_all_permissions_without_declarations(user, catalog_permission, db):
    user.is_superuser = True
    user.save()
    assert user.has_perm(PERM) is True
    assert user.has_perm("undeclared.perm.code") is True


def test_anonymous_user_has_no_permissions(db, catalog_permission):
    from django.contrib.auth.models import AnonymousUser

    assert PermissionBackend().has_perm(AnonymousUser(), PERM) is False
    assert user_permission_codenames(AnonymousUser()) == set()


def test_inactive_user_loses_permissions(user, catalog_permission, db):
    role = ensure_role("Viewers")
    role.permissions.add(catalog_permission)
    grant_role(user, "Viewers")
    assert user.has_perm(PERM) is True

    user.is_active = False
    user.save()
    assert user.has_perm(PERM) is False


def test_sync_plugin_permissions_creates_rows(db):
    from core.plugins.permissions import permission_registry

    permission_registry.register("sample_plugin", ["sample_plugin.view_greeting"])
    try:
        created = sync_plugin_permissions()
        assert created == 1

        permission = Permission.objects.get(codename="sample_plugin.view_greeting")
        assert permission.source == "sample_plugin"

        created_again = sync_plugin_permissions()
        assert created_again == 0
    finally:
        permission_registry.unregister("sample_plugin")
