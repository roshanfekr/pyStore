"""Canonical catalog of default permissions.

Single source of truth for the granular (dotted) permission codenames used
across the platform. They are seeded on first run:

- by the ``0003_seed_default_permissions`` data migration, and
- re-synced automatically after every ``migrate`` (``post_migrate`` signal).

Plugin permissions are handled separately: enabled plugins register their
codenames through ``PermissionRegistry`` (``source = plugin_id``).
"""

from apps.catalog.services import CATALOG_PERMISSIONS
from apps.cms.services import CMS_PERMISSIONS
from apps.inventory.services import INVENTORY_PERMISSIONS
from apps.orders.services import ORDER_PERMISSIONS
from apps.pricing.permissions import PRICING_PERMISSIONS
from apps.reviews.permissions import REVIEWS_PERMISSIONS
from apps.vendors.services import VENDOR_PERMISSIONS

CORE_PERMISSIONS: list[tuple[str, str]] = [
    ("identity.users.manage", "Manage users"),
    ("identity.roles.manage", "Manage roles and permissions"),
    ("stores.manage", "Manage stores and localization"),
]

DEFAULT_PERMISSIONS: list[tuple[str, str]] = [
    *CATALOG_PERMISSIONS,
    *ORDER_PERMISSIONS,
    *INVENTORY_PERMISSIONS,
    *CMS_PERMISSIONS,
    *PRICING_PERMISSIONS,
    *VENDOR_PERMISSIONS,
    *REVIEWS_PERMISSIONS,
    *CORE_PERMISSIONS,
]

DEFAULT_ROLE_NAMES = ("Administrators", "Vendors", "Customers")

ROLE_PERMISSIONS: dict[str, tuple[str, ...]] = {
    "Administrators": tuple(codename for codename, _ in DEFAULT_PERMISSIONS),
    "Vendors": (
        "vendor.view",
        "vendor.products.manage",
        "vendor.orders.view",
    ),
    "Customers": (),
}


def default_role_permission_map() -> dict[str, list[str]]:
    """Role name -> permission codenames granted by default."""
    return {role: list(codenames) for role, codenames in ROLE_PERMISSIONS.items()}
