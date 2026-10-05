import re

from django.db import transaction
from django.utils.text import slugify

from apps.stores.models import Store, StoreDomain
from core.exceptions import ConflictError, NotFoundError, ValidationError
from core.settings import SettingsError, settings_service


def _store_namespace(store: Store) -> str:
    return f"store:{store.id}"


def _unique_slug(name: str) -> str:
    base = slugify(name) or "store"
    slug = base
    counter = 2
    while Store.objects.filter(slug=slug).exists():
        slug = f"{base}-{counter}"
        counter += 1
    return slug


@transaction.atomic
def create_store(
    name: str,
    *,
    domains=None,
    default_language: str = "en",
    default_currency: str = "USD",
    supported_languages=None,
    supported_currencies=None,
    timezone_str: str = "UTC",
) -> Store:
    if not name or not name.strip():
        raise ValidationError("Store name is required", code="stores.name_required")

    store = Store.objects.create(
        name=name.strip(),
        slug=_unique_slug(name),
        default_language=default_language,
        default_currency=default_currency,
        supported_languages=supported_languages
        if supported_languages is not None
        else [default_language],
        supported_currencies=supported_currencies
        if supported_currencies is not None
        else [default_currency],
        timezone=timezone_str,
    )
    for domain in domains or []:
        add_store_domain(store, domain)
    return store


def ensure_default_store(name: str = "Main Store") -> Store:
    existing = Store.objects.filter(is_default=True).first()
    if existing is not None:
        return existing
    store = create_store(name)
    set_primary_store(store)
    return store


def add_store_domain(
    store: Store, domain: str, *, ssl_enabled: bool = True, is_primary: bool = False
) -> StoreDomain:
    domain = (domain or "").lower().strip()
    if not re.match(r"^[a-z0-9.-]+\.[a-z]{2,}$", domain):
        raise ValidationError("Invalid domain name", code="stores.invalid_domain")
    if StoreDomain.objects.filter(domain=domain).exists():
        raise ConflictError("Domain already in use", code="stores.domain_taken")
    return StoreDomain.objects.create(
        store=store, domain=domain, ssl_enabled=ssl_enabled, is_primary=is_primary
    )


def get_store_by_domain(domain: str) -> Store:
    store_domain = (
        StoreDomain.objects.filter(domain=(domain or "").lower().strip())
        .select_related("store")
        .first()
    )
    if store_domain is None:
        raise NotFoundError(f"No store found for domain {domain!r}", code="stores.domain_not_found")
    return store_domain.store


def set_primary_store(store: Store) -> None:
    Store.objects.exclude(pk=store.pk).update(is_default=False)
    store.is_default = True
    store.save(update_fields=["is_default"])


def set_store_status(store: Store, is_active: bool) -> Store:
    store.is_active = is_active
    store.save(update_fields=["is_active"])
    return store


def set_store_localization(
    store: Store,
    *,
    default_language=None,
    supported_languages=None,
    default_currency=None,
    supported_currencies=None,
    timezone_str=None,
) -> Store:
    if default_language:
        store.default_language = default_language
    if supported_languages:
        store.supported_languages = supported_languages
    if default_currency:
        store.default_currency = default_currency
    if supported_currencies:
        store.supported_currencies = supported_currencies
    if timezone_str:
        store.timezone = timezone_str
    store.save()
    return store


def get_store_setting(store: Store, key: str, default=None):
    try:
        return settings_service.get(_store_namespace(store), key)
    except SettingsError:
        return default


def set_store_setting(store: Store, key: str, value):
    return settings_service.set(_store_namespace(store), key, value)
