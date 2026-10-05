import re

from django.core.exceptions import ValidationError

PHONE_REGEX = re.compile(r"^\+?\d{10,15}$")


def validate_phone(value) -> None:
    if not PHONE_REGEX.match(str(value)):
        raise ValidationError("Enter a valid phone number.", code="invalid_phone")


def validate_non_blank(value) -> None:
    if value is None or not str(value).strip():
        raise ValidationError("This field must not be blank.", code="blank")


def validate_positive_integer(value) -> None:
    try:
        number = int(value)
    except (TypeError, ValueError):
        raise ValidationError("Enter a valid integer.", code="invalid_integer") from None
    if number <= 0:
        raise ValidationError("Value must be greater than zero.", code="not_positive")
