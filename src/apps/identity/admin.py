from django.contrib import admin

from .models import Customer, Permission, Role, User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("email", "user_type", "is_active", "is_staff", "email_verified")
    search_fields = ("email",)
    ordering = ("email",)
    fields = (
        "email",
        "first_name",
        "last_name",
        "user_type",
        "email_verified",
        "is_active",
        "is_staff",
        "is_superuser",
    )


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "phone")
    search_fields = ("user__email",)


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("name", "is_system", "display_permissions")
    search_fields = ("name",)

    @admin.display(description="Permissions")
    def display_permissions(self, obj: Role) -> str:
        return ", ".join(p.codename for p in obj.permissions.all()[:5])


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ("codename", "source", "display_name")
    search_fields = ("codename",)
    list_filter = ("source",)
