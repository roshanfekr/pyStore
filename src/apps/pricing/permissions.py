from apps.identity.services.roles import ensure_permission

PRICING_PERMISSIONS = [
    ("pricing.manage", "Manage pricing"),
    ("discounts.manage", "Manage discounts"),
    ("taxes.manage", "Manage taxes"),
]


def ensure_pricing_permissions() -> None:
    for codename, display_name in PRICING_PERMISSIONS:
        ensure_permission(codename, display_name=display_name, source="core")
