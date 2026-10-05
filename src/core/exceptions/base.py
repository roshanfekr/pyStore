class ApplicationError(Exception):
    message = "Application error"
    code = "application_error"
    status_code = 400

    def __init__(self, message: str | None = None, *, code: str | None = None, details=None):
        self.message = message or self.message
        self.code = code or self.code
        self.details = details
        super().__init__(self.message)


class ValidationError(ApplicationError):
    message = "Validation failed"
    code = "validation_error"
    status_code = 400


class NotFoundError(ApplicationError):
    message = "Resource not found"
    code = "not_found"
    status_code = 404


class PermissionDeniedError(ApplicationError):
    message = "Permission denied"
    code = "permission_denied"
    status_code = 403


class AuthenticationFailedError(ApplicationError):
    message = "Authentication failed"
    code = "authentication_failed"
    status_code = 401


class ConflictError(ApplicationError):
    message = "Conflict"
    code = "conflict"
    status_code = 409


class BusinessRuleError(ApplicationError):
    message = "Business rule violated"
    code = "business_rule_violation"
    status_code = 400


class ExternalServiceError(ApplicationError):
    message = "External service error"
    code = "external_service_error"
    status_code = 502


class UnexpectedError(ApplicationError):
    message = "Internal server error"
    code = "internal_error"
    status_code = 500
