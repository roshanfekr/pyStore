import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings as django_settings

ENCRYPTION_PREFIX = "enc:"


def _fernet() -> Fernet:
    key = getattr(django_settings, "SETTINGS_ENCRYPTION_KEY", None) or django_settings.SECRET_KEY
    derived = base64.urlsafe_b64encode(hashlib.sha256(str(key).encode()).digest())
    return Fernet(derived)


def is_encrypted(value) -> bool:
    return isinstance(value, str) and value.startswith(ENCRYPTION_PREFIX)


def encrypt_value(value: str) -> str:
    return ENCRYPTION_PREFIX + _fernet().encrypt(value.encode()).decode()


def decrypt_value(token: str) -> str:
    raw = token.removeprefix(ENCRYPTION_PREFIX)
    try:
        return _fernet().decrypt(raw.encode()).decode()
    except InvalidToken:
        from core.settings.service import SettingsError

        raise SettingsError("Failed to decrypt secure setting: invalid encryption key") from None
