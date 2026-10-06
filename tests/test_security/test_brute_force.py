import pytest
from django.contrib.auth import get_user_model

from apps.identity.services.authentication import authenticate_credentials
from core.exceptions import AuthenticationFailedError

User = get_user_model()
PASSWORD = "Str0ng!Passw0rd"


@pytest.fixture
def user(db):
    return User.objects.create_user(email="brute@example.com", password=PASSWORD)


def test_failed_login_is_counted(user, db, sync_delivery):
    with pytest.raises(AuthenticationFailedError):
        authenticate_credentials("brute@example.com", "Wrong!Pass1")

    from core.security.brute_force import failed_login_count

    assert failed_login_count("brute@example.com") == 1


def test_account_locks_after_max_failures(user, db, sync_delivery):
    for _ in range(5):
        with pytest.raises(AuthenticationFailedError):
            authenticate_credentials("brute@example.com", "Wrong!Pass1")

    with pytest.raises(AuthenticationFailedError) as exc_info:
        authenticate_credentials("brute@example.com", PASSWORD)

    assert exc_info.value.code == "identity.account_locked"


def test_successful_login_resets_counter(user, db, sync_delivery):
    with pytest.raises(AuthenticationFailedError):
        authenticate_credentials("brute@example.com", "Wrong!Pass1")

    authenticate_credentials("brute@example.com", PASSWORD)

    from core.security.brute_force import failed_login_count

    assert failed_login_count("brute@example.com") == 0


def test_locked_account_rejects_correct_password(user, db, sync_delivery):
    from core.security import brute_force

    for _ in range(brute_force.MAX_FAILED_LOGINS):
        brute_force.register_failed_login("brute@example.com")

    with pytest.raises(AuthenticationFailedError) as exc_info:
        authenticate_credentials("brute@example.com", PASSWORD)
    assert exc_info.value.code == "identity.account_locked"


def test_lockout_expiry_via_cache_ttl(user, db, sync_delivery):
    from django.core.cache import cache

    from core.security import brute_force

    cache.set(brute_force._key("brute@example.com"), brute_force.MAX_FAILED_LOGINS, 60)
    with pytest.raises(AuthenticationFailedError) as exc_info:
        authenticate_credentials("brute@example.com", PASSWORD)
    assert exc_info.value.code == "identity.account_locked"

    cache.delete(brute_force._key("brute@example.com"))
    assert authenticate_credentials("brute@example.com", PASSWORD).email == user.email
