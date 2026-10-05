from rest_framework.exceptions import NotFound

from core.error_handling import api_exception_handler
from core.exceptions import (
    ApplicationError,
    ConflictError,
    NotFoundError,
    ValidationError,
)


def test_drf_exception_wrapped_in_error_envelope():
    response = api_exception_handler(NotFound(), {})

    assert response.status_code == 404
    assert response.data["error"]["code"] == "not_found"
    assert response.data["error"]["message"] == "Not found."
    assert response.data["error"]["details"] is None


def test_validation_error_keeps_details():
    exc = NotFound("x")
    response = api_exception_handler(exc, {})
    assert response.data["error"]["message"]


def test_unhandled_exception_returns_server_error():
    response = api_exception_handler(ValueError("boom"), {})

    assert response.status_code == 500
    assert response.data["error"]["code"] == "server_error"
    assert response.data["error"]["message"] == "Internal server error"


def test_application_error_returns_envelope():
    exc = ApplicationError("Something failed", code="custom_error")
    response = api_exception_handler(exc, {})

    assert response.status_code == 400
    assert response.data["error"] == {
        "code": "custom_error",
        "message": "Something failed",
        "details": None,
    }


def test_application_error_defaults():
    exc = ApplicationError()
    assert exc.code == "application_error"
    assert exc.message == "Application error"


def test_not_found_error_maps_to_404():
    response = api_exception_handler(NotFoundError(), {})
    assert response.status_code == 404
    assert response.data["error"]["code"] == "not_found"


def test_conflict_error_maps_to_409():
    response = api_exception_handler(ConflictError(), {})
    assert response.status_code == 409


def test_validation_error_preserves_details():
    exc = ValidationError("bad input", details={"name": ["required"]})
    response = api_exception_handler(exc, {})
    assert response.status_code == 400
    assert response.data["error"]["details"] == {"name": ["required"]}
