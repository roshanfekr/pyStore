from rest_framework.authtoken.models import Token

from apps.identity.models import User
from core.audit.service import audit
from core.exceptions import AuthenticationFailedError
from core.security.brute_force import (
    assert_not_locked,
    clear_failed_logins,
    register_failed_login,
)


def authenticate_credentials(email: str, password: str, *, request=None) -> User:
    assert_not_locked(email)

    user = User.objects.filter(email__iexact=email).first()
    if user is None or not user.check_password(password or ""):
        register_failed_login(email)
        audit(
            "auth.login_failed",
            "user",
            email,
            request=request,
            after={"reason": "invalid_credentials"},
        )
        raise AuthenticationFailedError(
            "Invalid email or password", code="identity.invalid_credentials"
        )
    if not user.is_active:
        register_failed_login(email)
        audit(
            "auth.login_failed",
            "user",
            email,
            request=request,
            after={"reason": "account_disabled"},
        )
        raise AuthenticationFailedError("Account is disabled", code="identity.account_disabled")

    clear_failed_logins(email)
    audit("auth.login", "user", str(user.id), actor=user, request=request)
    return user


def issue_api_token(user) -> Token:
    token, _ = Token.objects.get_or_create(user=user)
    return token


def revoke_api_token(user) -> None:
    Token.objects.filter(user=user).delete()
    audit("auth.logout", "user", str(user.id), actor=user)
