from rest_framework.permissions import BasePermission


class HasPerm(BasePermission):
    perm_code = None

    def has_permission(self, request, view) -> bool:
        user = request.user
        if user is None or not user.is_authenticated:
            return False
        return user.has_perm(self.perm_code)


def has_perm(perm_code: str) -> type[HasPerm]:
    return type("HasPerm", (HasPerm,), {"perm_code": perm_code})
