"""Response security headers applied to every response."""

from django.conf import settings

DEFAULT_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "X-XSS-Protection": "0",
}

CSP_DIRECTIVES = (
    "default-src 'self'",
    "img-src 'self' data:",
    "style-src 'self' 'unsafe-inline'",
    "script-src 'self'",
    "object-src 'none'",
    "frame-ancestors 'none'",
)


class SecurityHeadersMiddleware:
    """Adds defensive headers that Django core does not set by default."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        for header, value in DEFAULT_HEADERS.items():
            response.headers.setdefault(header, value)
        csp = getattr(settings, "CONTENT_SECURITY_POLICY", "")
        if csp:
            response.headers.setdefault("Content-Security-Policy", csp)
        return response
