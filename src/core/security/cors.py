"""Minimal CORS support without an extra dependency.

Origins come from the ``CORS_ALLOWED_ORIGINS`` environment variable
(comma-separated). No CORS headers are emitted until it is configured,
keeping same-origin deployments unchanged.
"""

from django.conf import settings

ALLOWED_METHODS = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
ALLOWED_HEADERS = "Authorization, Content-Type, X-Store, X-Cart-Session, X-Requested-With"


def allowed_origins() -> list[str]:
    raw = getattr(settings, "CORS_ALLOWED_ORIGINS", []) or []
    return [origin.strip() for origin in raw if origin.strip()]


class CORSMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        origin = request.headers.get("Origin", "")
        is_allowed = bool(origin) and origin in allowed_origins()

        if request.method == "OPTIONS" and is_allowed:
            response = self._preflight_response()
        else:
            response = self.get_response(request)

        if is_allowed:
            response.headers.setdefault("Access-Control-Allow-Origin", origin)
        return response

    def _preflight_response(self):
        from django.http import HttpResponse

        response = HttpResponse(status=204)
        response.headers["Access-Control-Allow-Methods"] = ALLOWED_METHODS
        response.headers["Access-Control-Allow-Headers"] = ALLOWED_HEADERS
        response.headers["Access-Control-Max-Age"] = "86400"
        return response
