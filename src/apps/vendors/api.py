from rest_framework.permissions import BasePermission


class IsVendorMember(BasePermission):
    """Requires the request to target a vendor the user belongs to.

    The view must expose ``get_vendor()`` returning the vendor instance.
    """

    def has_permission(self, request, view) -> bool:
        from apps.vendors.services import user_can_manage_vendor

        vendor = view.get_vendor() if hasattr(view, "get_vendor") else None
        if vendor is None:
            return False
        return user_can_manage_vendor(request.user, vendor)


class IsVendorAdmin(BasePermission):
    def has_permission(self, request, view) -> bool:
        from apps.vendors.services import user_can_manage_vendor_users

        vendor = view.get_vendor() if hasattr(view, "get_vendor") else None
        if vendor is None:
            return False
        return user_can_manage_vendor_users(request.user, vendor)
