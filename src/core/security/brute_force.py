"""Brute-force protection for credential-based logins.

Failed attempts are tracked per email in the configured cache backend
(Redis in production, LocMem in tests). After ``AUTH_MAX_FAILED_LOGINS``
failures within the window the account is temporarily locked.
"""

import logging

from django.core.cache import cache

from core.exceptions import AuthenticationFailedError

logger = logging.getLogger(__name__)

FAILED_PREFIX = "auth:failed:"
MAX_FAILED_LOGINS = 5
FAILURE_WINDOW_SECONDS = 15 * 60
LOCK_WINDOW_SECONDS = 15 * 60


def _key(email: str) -> str:
    return f"{FAILED_PREFIX}{(email or '').strip().lower()}"


def failed_login_count(email: str) -> int:
    return int(cache.get(_key(email), 0))


def register_failed_login(email: str) -> int:
    try:
        count = failed_login_count(email) + 1
        cache.set(_key(email), count, FAILURE_WINDOW_SECONDS)
        if count >= MAX_FAILED_LOGINS:
            logger.warning("Account %s locked after %d failed logins", email, count)
        return count
    except Exception:
        logger.exception("Failed to record failed login for %s", email)
        return 0


def clear_failed_logins(email: str) -> None:
    try:
        cache.delete(_key(email))
    except Exception:
        logger.exception("Failed to clear failed logins for %s", email)


def assert_not_locked(email: str) -> None:
    if failed_login_count(email) >= MAX_FAILED_LOGINS:
        raise AuthenticationFailedError(
            "Too many failed attempts. Try again later.",
            code="identity.account_locked",
        )
