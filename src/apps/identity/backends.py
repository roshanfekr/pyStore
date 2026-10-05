from django.contrib.auth import get_user_model

User = get_user_model()


class PermissionBackend:
    """Grants granular dotted codenames (e.g. catalog.product.view) from roles."""

    def authenticate(self, request, **kwargs):
        return None

    def get_all_permissions(self, user_obj, obj=None) -> set[str]:
        if obj is not None or not user_obj.is_active or not getattr(user_obj, "is_authenticated", False):
            return set()
        if user_obj.is_superuser:
            from .models import Permission

            return set(Permission.objects.values_list("codename", flat=True))
        return set(
            User.roles.through.objects.filter(user=user_obj).values_list(
                "role__permissions__codename", flat=True
            )
        )

    def has_perm(self, user_obj, perm, obj=None) -> bool:
        return perm in self.get_all_permissions(user_obj, obj)


def user_permission_codenames(user) -> set[str]:
    if not getattr(user, "is_authenticated", False):
        return set()
    if user.is_superuser:
        from .models import Permission

        return set(Permission.objects.values_list("codename", flat=True))
    return set(
        User.roles.through.objects.filter(user=user).values_list(
            "role__permissions__codename", flat=True
        )
    )
