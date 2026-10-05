from rest_framework.authtoken.models import Token

from apps.identity.models import User
from core.exceptions import AuthenticationFailedError


def authenticate_credentials(email: str, password: str) -> User:
    user = User.objects.filter(email__iexact=email).first()
    if user is None or not user.check_password(password or ""):
        raise AuthenticationFailedError(
            "Invalid email or password", code="identity.invalid_credentials"
        )
    if not user.is_active:
        raise AuthenticationFailedError("Account is disabled", code="identity.account_disabled")
    return user


def issue_api_token(user) -> Token:
    token, _ = Token.objects.get_or_create(user=user)
    return token


def revoke_api_token(user) -> None:
    Token.objects.filter(user=user).delete()
