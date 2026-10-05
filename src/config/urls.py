from django.urls import include, path

from apps.admin_panel.admin_site import admin_site
from core.health.views import health_check

urlpatterns = [
    path("admin/", admin_site.urls),
    path("health/", health_check, name="health"),
    path("plugins/", include("core.plugins.urls")),
    path("", include("apps.storefront.urls")),
]
