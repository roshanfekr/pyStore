from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

from core.exceptions import ApplicationError


def api_exception_handler(exc, context):
    if isinstance(exc, ApplicationError):
        return Response(
            {
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": exc.details,
                }
            },
            status=exc.status_code,
        )

    response = drf_exception_handler(exc, context)

    if response is None:
        return Response(
            {
                "error": {
                    "code": "server_error",
                    "message": "Internal server error",
                    "details": None,
                }
            },
            status=500,
        )

    details = response.data
    message = "Request failed"
    if isinstance(details, dict) and "detail" in details:
        message = str(details["detail"])
        details = None

    response.data = {
        "error": {
            "code": getattr(exc, "default_code", None) or "error",
            "message": message,
            "details": details,
        }
    }
    return response
