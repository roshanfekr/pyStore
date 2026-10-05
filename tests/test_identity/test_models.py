import pytest
from django.contrib.auth import get_user_model

from apps.identity.models import Customer
from apps.identity.services.roles import ensure_default_roles, ensure_role

User = get_user_model()


@pytest.fixture
def with_default_roles(db):
    ensure_default_roles()


@pytest.fixture
def user(db, with_default_roles):
    return User.objects.create_user(
        email="customer@example.com", password="Str0ng!Passw0rd", first_name="Ali"
    )


@pytest.fixture
def role(db):
    return ensure_role("Managers", description="Manages catalog")


def test_create_user_hashes_password_and_defaults(db):
    user = User.objects.create_user(email="ali@example.com", password="Str0ng!Passw0rd")
    assert user.pk is not None
    assert user.check_password("Str0ng!Passw0rd")
    assert user.check_password("wrong") is False
    assert user.user_type == "customer"
    assert user.is_customer is True
    assert user.email_verified is False
    assert user.is_active is True
    assert str(user) == "ali@example.com"


def test_create_superuser_flags(db):
    admin = User.objects.create_superuser(email="admin@example.com", password="Str0ng!Passw0rd")
    assert admin.is_staff is True
    assert admin.is_superuser is True
    assert admin.is_staff_user is True


def test_email_is_unique(db):
    User.objects.create_user(email="dup@example.com", password="Str0ng!Passw0rd")
    from django.db import IntegrityError

    with pytest.raises(IntegrityError):
        User.objects.create_user(email="dup@example.com", password="Other!Passw0rd")


def test_email_lookup_is_case_insensitive(user):
    assert User.objects.filter(email__iexact="CUSTOMER@EXAMPLE.COM").exists()


def test_registration_creates_customer_and_assigns_role(with_default_roles):
    from apps.identity.services.registration import RegistrationService

    service = RegistrationService()
    result = service.run(email="profile@example.com", password="Str0ng!Passw0rd")
    user = result.value

    profile = Customer.objects.get(user=user)
    assert profile is not None
    assert user.roles.filter(name="Customers").exists()


def test_role_and_permission_models(db, role):
    from apps.identity.models import Permission

    perm = Permission.objects.create(codename="catalog.product.view", source="core")
    role.permissions.add(perm)
    assert list(role.permissions.all()) == [perm]
    assert perm.source == "core"
    assert str(perm) == "catalog.product.view"
