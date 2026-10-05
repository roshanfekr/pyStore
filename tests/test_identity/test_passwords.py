import pytest
from django.utils import timezone

from apps.identity.events import PasswordReset
from apps.identity.models import User
from apps.identity.services.passwords import (
    request_password_reset,
    reset_password,
)
from core.events import dispatcher
from core.exceptions import ValidationError

pytestmark = [pytest.mark.django_db]

PASSWORD = "Str0ng!Passw0rd"
NEW_PASSWORD = "N3w!Str0ngPass"


@pytest.fixture
def user(db):
    return User.objects.create_user(email="reset@example.com", password=PASSWORD)


def test_request_password_reset_creates_token(user):
    token = request_password_reset("reset@example.com")
    assert token is not None
    assert token.is_valid()


def test_request_password_reset_unknown_email_returns_none():
    assert request_password_reset("ghost@example.com") is None


def test_reset_password_changes_password(user):
    token = request_password_reset("reset@example.com")

    reset_user = reset_password(token.token, NEW_PASSWORD)

    assert reset_user.id == user.id
    user.refresh_from_db()
    assert user.check_password(NEW_PASSWORD)
    assert user.check_password(PASSWORD) is False
    token.refresh_from_db()
    assert token.used_at is not None


def test_reset_password_dispatches_event(user):
    received = []

    def handler(event):
        received.append(event)

    dispatcher.subscribe(PasswordReset, handler)
    try:
        token = request_password_reset("reset@example.com")
        reset_password(token.token, NEW_PASSWORD)
    finally:
        dispatcher.unsubscribe(PasswordReset, handler)

    assert len(received) == 1
    assert received[0].email == "reset@example.com"


def test_used_token_cannot_be_reused(user):
    token = request_password_reset("reset@example.com")
    reset_password(token.token, NEW_PASSWORD)

    with pytest.raises(ValidationError):
        reset_password(token.token, "An0ther!Str0ngPass")


def test_expired_token_rejected(user, db):
    from apps.identity.models import PasswordResetToken

    token = PasswordResetToken.objects.create(
        user=user, expires_at=timezone.now() - timezone.timedelta(hours=1)
    )
    assert token.is_valid() is False
    with pytest.raises(ValidationError):
        reset_password(token.token, NEW_PASSWORD)


def test_weak_new_password_rejected(user):
    token = request_password_reset("reset@example.com")
    with pytest.raises(ValidationError):
        reset_password(token.token, "weak")
    user.refresh_from_db()
    assert user.check_password(PASSWORD)
