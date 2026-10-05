import pytest

from apps.identity.models import User
from apps.identity.services.authentication import (
    authenticate_credentials,
    issue_api_token,
    revoke_api_token,
)
from core.exceptions import AuthenticationFailedError

pytestmark = [pytest.mark.django_db]

PASSWORD = "Str0ng!Passw0rd"


@pytest.fixture
def user(db):
    return User.objects.create_user(email="auth@example.com", password=PASSWORD)


def test_valid_credentials_return_user(user):
    authenticated = authenticate_credentials("auth@example.com", PASSWORD)
    assert authenticated.id == user.id


def test_case_insensitive_email(user):
    authenticated = authenticate_credentials("AUTH@EXAMPLE.COM", PASSWORD)
    assert authenticated.id == user.id


def test_wrong_password_raises(user):
    with pytest.raises(AuthenticationFailedError, match="Invalid"):
        authenticate_credentials("auth@example.com", "Wrong!Passw0rd")


def test_unknown_email_raises():
    with pytest.raises(AuthenticationFailedError):
        authenticate_credentials("ghost@example.com", PASSWORD)


def test_inactive_user_raises(user):
    user.is_active = False
    user.save()
    with pytest.raises(AuthenticationFailedError, match="disabled"):
        authenticate_credentials("auth@example.com", PASSWORD)


def test_api_token_issue_and_revoke(user):
    token = issue_api_token(user)
    assert token.key
    assert issue_api_token(user).key == token.key

    revoke_api_token(user)
    from rest_framework.authtoken.models import Token

    assert Token.objects.filter(user=user).exists() is False
