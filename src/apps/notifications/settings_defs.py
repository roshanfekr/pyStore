from core.settings.service import settings_service

NAMESPACE = "notifications"

_ENABLED_KEYS = {
    "email": "email_enabled",
    "inapp": "inapp_enabled",
    "webhook": "webhook_enabled",
    "sms": "sms_enabled",
}


def register_notification_settings() -> None:
    for channel, key in _ENABLED_KEYS.items():
        settings_service.register(NAMESPACE, key, default=True, value_type=bool)
        settings_service.register(NAMESPACE, f"{channel}_provider", default="", value_type=str)
    settings_service.register(NAMESPACE, "async_delivery", default=True, value_type=bool)
    settings_service.register(NAMESPACE, "max_attempts", default=5, value_type=int)
    settings_service.register(NAMESPACE, "webhook_timeout", default=10, value_type=int)


def channel_enabled(channel: str) -> bool:
    return bool(settings_service.get(NAMESPACE, _ENABLED_KEYS[channel]))


def enabled_channels() -> list[str]:
    return [channel for channel in _ENABLED_KEYS if channel_enabled(channel)]


def max_attempts() -> int:
    try:
        attempts = int(settings_service.get(NAMESPACE, "max_attempts"))
    except (TypeError, ValueError):
        return 5
    return max(1, attempts)


def async_delivery_enabled() -> bool:
    return bool(settings_service.get(NAMESPACE, "async_delivery"))


def channel_provider_setting(channel: str) -> str:
    return str(settings_service.get(NAMESPACE, f"{channel}_provider") or "")
