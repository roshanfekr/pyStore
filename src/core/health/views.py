from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from core.health.checks import run_health_checks


@api_view(["GET"])
@permission_classes([AllowAny])
def health_check(request):
    checks = run_health_checks()
    is_healthy = all(status == "ok" for status in checks.values())
    return Response(
        {
            "status": "ok" if is_healthy else "degraded",
            "checks": checks,
        },
        status=200 if is_healthy else 503,
    )
