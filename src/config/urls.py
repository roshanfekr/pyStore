from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path

from apps.admin_panel.admin_site import admin_site
from core.health.views import health_check

urlpatterns = [
    path("admin/", admin_site.urls),
    path("health/", health_check, name="health"),
    path("api/<str:version>/", include("config.api_urls")),
    path("plugins/", include("core.plugins.urls")),
    path("", include("apps.storefront.urls")),
]

if settings.DEBUG:
    # Serve uploaded product/media files during development.
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
