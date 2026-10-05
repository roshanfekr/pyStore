from django.contrib.auth.password_validation import validate_password as django_validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone

from apps.identity.events import PasswordReset
from apps.identity.models import PASSWORD_RESET_TTL, PasswordResetToken, User
from core.events import dispatcher
from core.exceptions import ValidationError


def _validate_new_password(password: str) -> None:
    try:
        django_validate_password(password)
    except DjangoValidationError as exc:
        raise ValidationError("Invalid password", details={"password": exc.messages}) from None


def request_password_reset(email: str):
    user = User.objects.filter(email__iexact=email, is_active=True).first()
    if user is None:
        return None
    return PasswordResetToken.objects.create(
        user=user, expires_at=timezone.now() + PASSWORD_RESET_TTL
    )


def reset_password(token, new_password: str) -> User:
    reset_token = PasswordResetToken.objects.filter(token=token).first()
    if reset_token is None or not reset_token.is_valid():
        raise ValidationError(
            "Invalid or expired reset token", code="identity.invalid_reset_token"
        )

    _validate_new_password(new_password)

    user = reset_token.user
    user.set_password(new_password)
    user.save(update_fields=["password"])
    reset_token.used_at = timezone.now()
    reset_token.save(update_fields=["used_at"])

    dispatcher.dispatch(PasswordReset(email=user.email))
    return user
