from apps.identity.models import Permission, Role
from core.exceptions import NotFoundError


def ensure_role(name: str, description: str = "", is_system: bool = False) -> Role:
    role, _ = Role.objects.get_or_create(
        name=name, defaults={"description": description, "is_system": is_system}
    )
    return role


def ensure_permission(codename: str, display_name: str = "", source: str = "core"):
    permission, created = Permission.objects.get_or_create(
        codename=codename,
        defaults={"display_name": display_name or codename, "source": source},
    )
    return permission, created


def grant_role(user, role_name: str) -> Role:
    try:
        role = Role.objects.get(name=role_name)
    except Role.DoesNotExist:
        raise NotFoundError(f"Role {role_name!r} not found", code="identity.role_not_found") from None
    user.roles.add(role)
    return role


def revoke_role(user, role_name: str) -> None:
    user.roles.filter(name=role_name).delete()


def ensure_default_roles() -> None:
    ensure_role("Administrators", "Full store administration", is_system=True)
    ensure_role("Vendors", "Vendor portal access", is_system=True)
    ensure_role("Customers", "Default customer role", is_system=True)


def sync_default_permissions() -> int:
    """Seed every default permission codename. Idempotent; returns created count."""
    from apps.identity.permissions import DEFAULT_PERMISSIONS

    created = 0
    for codename, display_name in DEFAULT_PERMISSIONS:
        _, was_created = ensure_permission(codename, display_name=display_name, source="core")
        if was_created:
            created += 1
    return created


def sync_default_role_permissions() -> None:
    """Ensure default roles exist and carry their default permission sets."""
    from apps.identity.permissions import default_role_permission_map

    ensure_default_roles()
    permission_by_code = {p.codename: p for p in Permission.objects.all()}
    for role_name, codenames in default_role_permission_map().items():
        role = Role.objects.get(name=role_name)
        if role_name == "Administrators":
            # Administrators always hold every permission, including ones
            # added later (e.g. by plugins or future features).
            role.permissions.set(Permission.objects.all())
            continue
        role.permissions.set(
            [permission_by_code[code] for code in codenames if code in permission_by_code]
        )


def sync_defaults() -> None:
    """Full default seed: permissions then role assignments."""
    sync_default_permissions()
    sync_default_role_permissions()


def sync_plugin_permissions() -> int:
    from core.plugins.permissions import permission_registry

    created = 0
    for plugin_id in permission_registry.plugins():
        for codename in permission_registry.for_plugin(plugin_id):
            _, was_created = ensure_permission(codename, source=plugin_id)
            if was_created:
                created += 1
    return created
