import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory

from apps.identity.services.roles import ensure_permission, ensure_role, grant_role
from apps.stores.services import create_store
from apps.vendors.api import IsVendorAdmin, IsVendorMember
from apps.vendors.events import VendorCreated
from apps.vendors.models import Vendor, VendorUser
from apps.vendors.services import (
    add_vendor_user,
    create_vendor,
    remove_vendor_user,
    set_vendor_status,
    user_can_manage_vendor,
    user_can_manage_vendor_users,
    vendors_for_user,
)
from core.events import dispatcher
from core.exceptions import ConflictError, ValidationError

User = get_user_model()

pytestmark = [pytest.mark.django_db]

PASSWORD = "Str0ng!Passw0rd"


@pytest.fixture
def store(db):
    return create_store("Vendor Store")


@pytest.fixture
def owner(db, store):
    return User.objects.create_user(email="owner@example.com", password=PASSWORD)


@pytest.fixture
def vendor(owner, store):
    return create_vendor(owner=owner, name="Acme Supplies", store=store)


@pytest.fixture
def stranger(db):
    return User.objects.create_user(email="stranger@example.com", password=PASSWORD)


def test_create_vendor_assigns_owner_admin_and_role(owner, store):
    vendor = create_vendor(owner=owner, name="Fresh Vendor", store=store, email="hi@acme.io")

    assert vendor.status == Vendor.STATUS_PENDING
    assert VendorUser.objects.filter(vendor=vendor, user=owner, is_admin=True).exists()
    assert owner.roles.filter(name="Vendors").exists()
    assert vendor.slug == "fresh-vendor"


def test_create_vendor_dispatches_event(owner, store):
    received = []

    def handler(event):
        received.append(event)

    dispatcher.subscribe(VendorCreated, handler)
    try:
        create_vendor(owner=owner, name="Event Vendor", store=store)
    finally:
        dispatcher.unsubscribe(VendorCreated, handler)

    assert len(received) == 1
    assert received[0].name == "Event Vendor"


def test_create_vendor_requires_name(owner, store):
    with pytest.raises(ValidationError):
        create_vendor(owner=owner, name="  ", store=store)


def test_owner_can_manage_vendor(vendor, owner):
    assert user_can_manage_vendor(owner, vendor) is True
    assert user_can_manage_vendor_users(owner, vendor) is True


def test_stranger_cannot_manage_vendor(vendor, stranger):
    assert user_can_manage_vendor(stranger, vendor) is False
    assert user_can_manage_vendor_users(stranger, vendor) is False


def test_add_and_remove_vendor_user(vendor, owner, stranger):
    add_vendor_user(actor=owner, vendor=vendor, user=stranger)
    assert VendorUser.objects.filter(vendor=vendor, user=stranger, is_admin=False).exists()
    assert user_can_manage_vendor(stranger, vendor) is True
    assert user_can_manage_vendor_users(stranger, vendor) is False

    remove_vendor_user(actor=owner, vendor=vendor, user=stranger)
    assert user_can_manage_vendor(stranger, vendor) is False


def test_cannot_add_member_twice(vendor, owner, stranger):
    add_vendor_user(actor=owner, vendor=vendor, user=stranger)
    with pytest.raises(ConflictError):
        add_vendor_user(actor=owner, vendor=vendor, user=stranger)


def test_only_vendor_admin_manages_members(vendor, owner, stranger):
    member = User.objects.create_user(email="member@example.com", password=PASSWORD)
    add_vendor_user(actor=owner, vendor=vendor, user=member)

    newcomer = User.objects.create_user(email="newcomer@example.com", password=PASSWORD)
    with pytest.raises(ConflictError):
        add_vendor_user(actor=member, vendor=vendor, user=newcomer)


def test_owner_cannot_be_removed(vendor, owner):
    with pytest.raises(ValidationError):
        remove_vendor_user(actor=owner, vendor=vendor, user=owner)


def test_vendor_status_transitions(vendor, owner):
    set_vendor_status(actor=owner, vendor=vendor, new_status=Vendor.STATUS_ACTIVE)
    vendor.refresh_from_db()
    assert vendor.status == Vendor.STATUS_ACTIVE

    set_vendor_status(actor=owner, vendor=vendor, new_status=Vendor.STATUS_DISABLED)
    vendor.refresh_from_db()
    assert vendor.status == Vendor.STATUS_DISABLED

    set_vendor_status(actor=owner, vendor=vendor, new_status=Vendor.STATUS_ACTIVE)
    vendor.refresh_from_db()
    assert vendor.status == Vendor.STATUS_ACTIVE


def test_invalid_status_transition_rejected(vendor, owner):
    set_vendor_status(actor=owner, vendor=vendor, new_status=Vendor.STATUS_ACTIVE)
    vendor.refresh_from_db()
    assert vendor.status == Vendor.STATUS_ACTIVE

    with pytest.raises(ValidationError):
        set_vendor_status(actor=owner, vendor=vendor, new_status=Vendor.STATUS_ACTIVE)
    vendor.refresh_from_db()
    assert vendor.status == Vendor.STATUS_ACTIVE


def test_stranger_cannot_change_status(vendor, stranger):
    with pytest.raises(ConflictError):
        set_vendor_status(actor=stranger, vendor=vendor, new_status=Vendor.STATUS_ACTIVE)


def test_vendors_for_user_scoping(owner, vendor, store, stranger):
    other_owner = User.objects.create_user(email="other@example.com", password=PASSWORD)
    other = create_vendor(owner=other_owner, name="Other Vendor", store=store)

    owned = vendors_for_user(owner)
    assert vendor.id in {v.id for v in owned}
    assert other.id not in {v.id for v in owned}

    assert vendors_for_user(stranger).count() == 0


def test_superuser_sees_all_vendors(owner, vendor, store, stranger):
    stranger.is_superuser = True
    stranger.save()
    assert vendors_for_user(stranger).count() == 1


def test_vendor_soft_delete(vendor):
    vendor.delete()
    assert Vendor.objects.filter(pk=vendor.pk).exists() is False
    assert Vendor.all_objects.filter(pk=vendor.pk).exists()


def test_vendor_permissions_declared(db):
    from apps.identity.models import Permission

    ensure_permission("vendor.view", source="core")
    assert Permission.objects.filter(codename="vendor.view").exists()

    ensure_role("Vendors")
    owner = User.objects.create_user(email="perm@example.com", password=PASSWORD)
    grant_role(owner, "Vendors")


def test_drf_vendor_membership_permissions(vendor, owner, stranger, store):
    view_stub = type("ViewStub", (), {"get_vendor": lambda self: vendor})

    member_request = APIRequestFactory().get("/")
    member_request.user = owner
    assert IsVendorMember().has_permission(member_request, view_stub()) is True
    assert IsVendorAdmin().has_permission(member_request, view_stub()) is True

    stranger_request = APIRequestFactory().get("/")
    stranger_request.user = stranger
    assert IsVendorMember().has_permission(stranger_request, view_stub()) is False
    assert IsVendorAdmin().has_permission(stranger_request, view_stub()) is False
