import pytest

from core.exceptions import (
    ApplicationError,
    AuthenticationFailedError,
    BusinessRuleError,
    ConflictError,
    ExternalServiceError,
    NotFoundError,
    PermissionDeniedError,
    UnexpectedError,
    ValidationError,
)


@pytest.mark.parametrize(
    "exc_class,code,status",
    [
        (ApplicationError, "application_error", 400),
        (ValidationError, "validation_error", 400),
        (BusinessRuleError, "business_rule_violation", 400),
        (NotFoundError, "not_found", 404),
        (PermissionDeniedError, "permission_denied", 403),
        (AuthenticationFailedError, "authentication_failed", 401),
        (ConflictError, "conflict", 409),
        (ExternalServiceError, "external_service_error", 502),
        (UnexpectedError, "internal_error", 500),
    ],
)
def test_exception_hierarchy_defaults(exc_class, code, status):
    exc = exc_class()
    assert exc.code == code
    assert exc.status_code == status
    assert exc.details is None


def test_custom_message_and_code():
    exc = NotFoundError("Product missing", code="product.not_found")
    assert exc.message == "Product missing"
    assert exc.code == "product.not_found"
    assert str(exc) == "Product missing"


def test_details_are_stored():
    exc = ValidationError("Invalid", details={"name": ["required"]})
    assert exc.details == {"name": ["required"]}


def test_all_subclasses_inherit_application_error():
    for exc_class in [ValidationError, NotFoundError, ConflictError]:
        assert issubclass(exc_class, ApplicationError)
