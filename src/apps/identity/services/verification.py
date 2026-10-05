from django.utils import timezone

from apps.identity.models import EMAIL_VERIFICATION_TTL, EmailVerificationToken
from core.exceptions import ValidationError


def issue_email_verification(user) -> EmailVerificationToken:
    return EmailVerificationToken.objects.create(
        user=user, expires_at=timezone.now() + EMAIL_VERIFICATION_TTL
    )


def verify_email(token) -> object:
    verification_token = EmailVerificationToken.objects.filter(token=token).first()
    if verification_token is None or not verification_token.is_valid():
        raise ValidationError(
            "Invalid or expired verification token", code="identity.invalid_verification_token"
        )

    user = verification_token.user
    user.email_verified = True
    user.save(update_fields=["email_verified"])

    verification_token.used_at = timezone.now()
    verification_token.save(update_fields=["used_at"])
    return user
