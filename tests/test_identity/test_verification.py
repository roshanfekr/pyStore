import pytest
from django.utils import timezone

from apps.identity.models import EmailVerificationToken, User
from apps.identity.services.verification import issue_email_verification, verify_email
from core.exceptions import ValidationError

pytestmark = [pytest.mark.django_db]


@pytest.fixture
def user(db):
    return User.objects.create_user(email="verify@example.com", password="Str0ng!Passw0rd")


def test_issue_and_verify_email(user):
    token = issue_email_verification(user)

    verified_user = verify_email(token.token)

    assert verified_user.id == user.id
    user.refresh_from_db()
    assert user.email_verified is True
    token.refresh_from_db()
    assert token.used_at is not None


def test_invalid_token_rejected():
    with pytest.raises(ValidationError):
        verify_email("00000000-0000-0000-0000-000000000000")


def test_expired_token_rejected(user):

    token = EmailVerificationToken.objects.create(
        user=user, expires_at=timezone.now() - timezone.timedelta(hours=1)
    )
    with pytest.raises(ValidationError):
        verify_email(token.token)


def test_token_cannot_be_reused(user):
    token = issue_email_verification(user)
    verify_email(token.token)

    with pytest.raises(ValidationError):
        verify_email(token.token)
