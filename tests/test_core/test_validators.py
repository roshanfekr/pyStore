import pytest
from django.core.exceptions import ValidationError as DjangoValidationError

from core.validators import validate_non_blank, validate_phone, validate_positive_integer


@pytest.mark.parametrize("value", ["+989121234567", "09121234567", "09121123456"])
def test_valid_phone(value):
    validate_phone(value)


@pytest.mark.parametrize("value", ["abc", "+", "123456789", "+1a2345678", ""])
def test_invalid_phone(value):
    with pytest.raises(DjangoValidationError):
        validate_phone(value)


@pytest.mark.parametrize("value", ["hello", " x ", 123])
def test_valid_non_blank(value):
    validate_non_blank(value)


@pytest.mark.parametrize("value", [None, "", "   "])
def test_invalid_non_blank(value):
    with pytest.raises(DjangoValidationError):
        validate_non_blank(value)


@pytest.mark.parametrize("value", [1, "5", 100])
def test_valid_positive_integer(value):
    validate_positive_integer(value)


@pytest.mark.parametrize("value", [0, -3, "abc", None])
def test_invalid_positive_integer(value):
    with pytest.raises(DjangoValidationError):
        validate_positive_integer(value)
