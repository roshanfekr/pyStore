import pytest
from django.contrib.auth import get_user_model

from apps.identity.models import Permission, Role
from apps.identity.permissions import DEFAULT_PERMISSIONS, default_role_permission_map
from apps.identity.services.roles import (
    grant_role,
    sync_default_permissions,
    sync_defaults,
)

User = get_user_model()

pytestmark = [pytest.mark.django_db]


@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser(email="perm-admin@example.com", password="Str0ng!Passw0rd")


@pytest.fixture
def staff_user(db):
    return User.objects.create_user(
        email="perm-staff@example.com", password="Str0ng!Passw0rd", is_staff=True
    )


def test_all_default_permissions_seeded(db):
    codenames = set(Permission.objects.values_list("codename", flat=True))
    for codename, _ in DEFAULT_PERMISSIONS:
        assert codename in codenames, f"missing default permission {codename}"


def test_seed_is_idempotent(db):
    assert sync_default_permissions() == 0
    assert sync_default_permissions() == 0


def test_administrators_role_has_all_permissions(db):
    role = Role.objects.get(name="Administrators")
    assert set(role.permissions.values_list("codename", flat=True)) == {
        codename for codename, _ in DEFAULT_PERMISSIONS
    }


def test_vendors_role_default_permissions(db):
    role = Role.objects.get(name="Vendors")
    expected = set(default_role_permission_map()["Vendors"])
    assert set(role.permissions.values_list("codename", flat=True)) == expected
    assert "catalog.product.delete" not in expected


def test_role_grants_enforced_permission(staff_user):
    grant_role(staff_user, "Administrators")
    assert staff_user.has_perm("order.cancel") is True
    assert staff_user.has_perm("identity.users.manage") is True


def test_staff_without_role_lacks_permissions(staff_user):
    assert staff_user.has_perm("order.cancel") is False
    assert staff_user.has_perm("identity.users.manage") is False


def test_superuser_has_every_permission(admin_user):
    for codename, _ in DEFAULT_PERMISSIONS:
        assert admin_user.has_perm(codename) is True


def test_user_admin_gated_by_identity_permission(client, staff_user, admin_user):
    client.force_login(staff_user)
    response = client.get("/admin/identity/user/add/")
    assert response.status_code == 403

    grant_role(staff_user, "Administrators")
    client.force_login(staff_user)
    response = client.get("/admin/identity/user/add/")
    assert response.status_code == 200


def test_sync_defaults_reassigns_new_permissions(db):
    sync_defaults()
    from apps.identity.models import Permission as P

    P.objects.create(codename="future.feature.manage", display_name="Future", source="core")
    sync_defaults()

    admins = Role.objects.get(name="Administrators").permissions.values_list("codename", flat=True)
    assert "future.feature.manage" in set(admins)
