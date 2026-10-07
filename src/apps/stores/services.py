import re

from django.db import transaction
from django.utils.text import slugify

from apps.stores.models import Language, LocaleStringResource, Store, StoreDomain
from core.exceptions import ConflictError, NotFoundError, ValidationError
from core.settings import SettingsError, settings_service

_translation_cache: dict[str, dict[str, str]] = {}


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


def ensure_default_language(name: str = "English", code: str = "en") -> Language:
    existing = Language.objects.filter(is_default=True).first()
    if existing is not None:
        return existing
    language, _ = Language.objects.get_or_create(
        code=code,
        defaults={"name": name, "is_active": True, "is_default": True},
    )
    return language


def upsert_language(
    name: str,
    code: str,
    *,
    is_active: bool = True,
    direction: str | None = None,
    flag: str = "",
    ordering: int = 0,
) -> Language:
    if not name.strip() or not code.strip():
        raise ValidationError("Language name and code are required", code="stores.language_invalid")
    code = code.strip().lower()
    existing = Language.objects.filter(code=code).first()
    defaults = {
        "name": name.strip(),
        "is_active": is_active,
        "direction": direction or (existing.direction if existing else "ltr"),
        "flag": flag,
        "ordering": ordering,
    }
    if existing is None:
        return Language.objects.create(code=code, **defaults)
    for field, value in defaults.items():
        setattr(existing, field, value)
    existing.save()
    return existing


def get_active_languages() -> list[Language]:
    return list(Language.objects.filter(is_active=True).order_by("ordering", "code"))


def get_default_language() -> Language | None:
    return Language.objects.filter(is_default=True).first()


def set_default_language(language: Language) -> Language:
    language.is_default = True
    language.save()
    return language


def get_active_language_code(cookie_code: str | None = None) -> str:
    """Resolve the active language: cookie choice → DB default → 'en'."""
    if cookie_code:
        code = cookie_code.split("-")[0].lower()
        if Language.objects.filter(code=code, is_active=True).exists():
            return code
    default = get_default_language()
    if default is not None and default.is_active:
        return default.code
    return "en"


def get_language(code: str) -> Language | None:
    return Language.objects.filter(code=code, is_active=True).first()


def clear_translation_cache() -> None:
    _translation_cache.clear()


def _catalog_for(code: str) -> dict[str, str]:
    catalog = _translation_cache.get(code)
    if catalog is None:
        catalog = dict(
            LocaleStringResource.objects.filter(language__code=code, language__is_active=True)
            .exclude(value="")
            .values_list("key", "value")
        )
        _translation_cache[code] = catalog
    return catalog


def lookup_translation(code: str, key: str, **format_kwargs) -> str:
    """Translate `key` for `code`; falls back to the source string."""
    value = _catalog_for(code).get(key, "").strip()
    result = value or key
    if format_kwargs:
        try:
            result = result.format(**format_kwargs)
        except (KeyError, IndexError, ValueError):
            pass
    return result


def seed_language_resources(code: str, mapping: dict[str, str]) -> int:
    """Upsert a word collection for a language. Returns created count.

    Key matching is case-insensitive (SQL Server unique indexes are
    case-insensitive by default collation).
    """
    language = Language.objects.filter(code=code).first()
    if language is None:
        return 0
    created = 0
    existing: dict[str, int] = {}
    for key, resource_id in LocaleStringResource.objects.filter(language=language).values_list(
        "key", "id"
    ):
        existing.setdefault(key.lower(), resource_id)
    for key, value in mapping.items():
        resource_id = existing.get(key.lower())
        if resource_id is not None:
            resource = LocaleStringResource.objects.get(pk=resource_id)
            if resource.value != value:
                resource.value = value
                resource.save(update_fields=["value", "updated_at"])
        else:
            resource = LocaleStringResource.objects.create(
                language=language, key=key[:255], value=value
            )
            existing[key.lower()] = resource.id
            created += 1
    clear_translation_cache()
    return created


def collect_template_strings() -> list[str]:
    """Scan storefront templates for {{ tr "..." }} keys; upsert for active languages.

    Returns the sorted list of discovered keys.
    """
    from pathlib import Path

    from django.conf import settings

    pattern = re.compile(r"tr\s+[\"'](.+?)[\"']")
    roots = [
        Path(settings.BASE_DIR) / "apps" / "storefront" / "templates",
        Path(settings.BASE_DIR) / "themes",
        Path(settings.BASE_DIR) / "plugins",
    ]
    keys: set[str] = set()
    for root in roots:
        if not root.exists():
            continue
        for template_file in root.rglob("*.html"):
            try:
                content = template_file.read_text(encoding="utf-8")
            except OSError:
                continue
            keys.update(match.strip() for match in pattern.findall(content))

    for language in Language.objects.filter(is_active=True):
        seed_language_resources(language.code, {key: "" for key in keys})
    return sorted(keys)
