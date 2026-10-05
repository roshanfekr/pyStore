
from django.db import transaction
from django.utils.text import slugify

from apps.identity.models import User
from apps.identity.services.roles import ensure_permission, ensure_role, grant_role
from apps.vendors.events import VendorCreated, VendorStatusChanged
from apps.vendors.models import Vendor, VendorUser
from core.events import dispatcher
from core.exceptions import ConflictError, ValidationError
from core.infrastructure import atomic

VENDOR_PERMISSIONS = [
    ("vendor.view", "View vendor"),
    ("vendor.manage", "Manage vendor"),
    ("vendor.users.manage", "Manage vendor users"),
    ("vendor.products.manage", "Manage vendor products"),
    ("vendor.orders.view", "View vendor orders"),
]


def ensure_vendor_permissions() -> None:
    for codename, display_name in VENDOR_PERMISSIONS:
        ensure_permission(codename, display_name=display_name, source="core")


def _unique_vendor_slug(name: str) -> str:
    base = slugify(name) or "vendor"
    slug = base
    counter = 2
    while Vendor.objects.filter(slug=slug).exists():
        slug = f"{base}-{counter}"
        counter += 1
    return slug


@transaction.atomic
def create_vendor(owner: User, name: str, store, *, email: str = "", description: str = "") -> Vendor:
    if not name or not name.strip():
        raise ValidationError("Vendor name is required", code="vendors.name_required")

    vendor = Vendor.objects.create(
        name=name.strip(),
        slug=_unique_vendor_slug(name),
        email=email,
        description=description,
        store=store,
        owner=owner,
    )
    VendorUser.objects.create(vendor=vendor, user=owner, is_admin=True)

    ensure_role("Vendors", is_system=True)
    grant_role(owner, "Vendors")
    ensure_vendor_permissions()

    dispatcher.dispatch(VendorCreated(vendor_id=str(vendor.id), name=vendor.name))
    return vendor


def add_vendor_user(actor: User, vendor: Vendor, user: User, *, is_admin: bool = False) -> VendorUser:
    if not user_can_manage_vendor_users(actor, vendor):
        raise ConflictError("Actor cannot manage vendor users", code="vendors.forbidden")
    if VendorUser.objects.filter(vendor=vendor, user=user).exists():
        raise ConflictError("User already belongs to this vendor", code="vendors.already_member")
    return VendorUser.objects.create(vendor=vendor, user=user, is_admin=is_admin)


def remove_vendor_user(actor: User, vendor: Vendor, user: User) -> None:
    if not user_can_manage_vendor_users(actor, vendor):
        raise ConflictError("Actor cannot manage vendor users", code="vendors.forbidden")
    if vendor.owner_id == user.id:
        raise ValidationError("Vendor owner cannot be removed", code="vendors.owner_protected")
    VendorUser.objects.filter(vendor=vendor, user=user).delete()


def user_can_manage_vendor(user, vendor) -> bool:
    if not getattr(user, "is_authenticated", False):
        return False
    if user.is_superuser:
        return True
    return VendorUser.objects.filter(vendor=vendor, user=user).exists()


def user_can_manage_vendor_users(user, vendor) -> bool:
    if not getattr(user, "is_authenticated", False):
        return False
    if user.is_superuser:
        return True
    return VendorUser.objects.filter(vendor=vendor, user=user, is_admin=True).exists()


def vendors_for_user(user):
    if not getattr(user, "is_authenticated", False):
        return Vendor.objects.none()
    if user.is_superuser:
        return Vendor.objects.all()
    return Vendor.objects.filter(memberships__user=user)


@atomic()
def set_vendor_status(actor: User, vendor: Vendor, new_status: str) -> Vendor:
    if not user_can_manage_vendor(actor, vendor):
        raise ConflictError("Actor cannot manage this vendor", code="vendors.forbidden")
    allowed = Vendor.ALLOWED_TRANSITIONS.get(vendor.status, set())
    if new_status not in allowed:
        raise ValidationError(
            f"Transition {vendor.status!r} -> {new_status!r} is not allowed",
            code="vendors.invalid_transition",
        )
    vendor.status = new_status
    vendor.save(update_fields=["status"])
    dispatcher.dispatch(VendorStatusChanged(vendor_id=str(vendor.id), new_status=new_status))
    return vendor
