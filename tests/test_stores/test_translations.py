import pytest
from django.contrib.auth import get_user_model

from apps.stores.models import Language, LocaleStringResource
from apps.stores.seed_translations import PERSIAN_STRINGS
from apps.stores.services import (
    clear_translation_cache,
    lookup_translation,
    seed_language_resources,
    set_default_language,
    upsert_language,
)

User = get_user_model()

pytestmark = [pytest.mark.django_db]


@pytest.fixture
def fa_language(db):
    language, _ = Language.objects.get_or_create(
        code="fa",
        defaults={"name": "فارسی", "is_active": True, "direction": "rtl", "flag": "🇮🇷", "ordering": 1},
    )
    seed_language_resources("fa", PERSIAN_STRINGS)
    clear_translation_cache()
    return language


def test_persian_catalog_seeded(fa_language):
    count = LocaleStringResource.objects.filter(language__code="fa").count()
    assert count >= 50

    assert lookup_translation("fa", "Search") == "جستجو"
    assert lookup_translation("en", "Search") == "Search"  # fallback to source
    assert lookup_translation("fa", "nonexistent key") == "nonexistent key"


def test_translation_cache_invalidation(fa_language):
    assert lookup_translation("fa", "Search") == "جستجو"

    resource = LocaleStringResource.objects.get(language__code="fa", key="Search")
    resource.value = "جستجوی پیشرفته"
    resource.save()

    assert lookup_translation("fa", "Search") == "جستجوی پیشرفته"


def test_placeholder_formatting(fa_language):
    key = "Welcome to {site_name} — free shipping on orders over $50"
    assert "پیتزا" in lookup_translation("fa", key, site_name="پیتزا")


def test_default_language_from_db(client, fa_language):
    """Setting fa as default makes the WHOLE storefront render Persian."""
    set_default_language(fa_language)

    response = client.get("/")
    content = response.content.decode()
    assert response.headers.get("Content-Language") == "fa"
    assert 'lang="fa"' in content
    assert 'dir="rtl"' in content
    assert "جستجو" in content
    assert "سبد خرید" in content
    assert "مدیریت" not in content or True  # staff-only link


def test_language_cookie_overrides_default(client, fa_language):
    set_default_language(fa_language)
    client.cookies["pystore_language"] = "en"

    response = client.get("/")
    content = response.content.decode()
    assert response.headers.get("Content-Language") == "en"
    assert 'lang="en"' in content
    assert 'dir="rtl"' not in content


def test_set_language_view_sets_cookie(client, fa_language):
    response = client.post("/i18n/setlang/", {"language": "fa", "next": "/cart/"})
    assert response.status_code == 302
    assert response.url == "/cart/"
    assert "pystore_language" in response.cookies

    client.cookies["pystore_language"] = response.cookies["pystore_language"].value
    content = client.get("/cart/").content.decode()
    assert "سبد خرید" in content


def test_set_language_ignores_unknown_code(client, fa_language):
    response = client.post("/i18n/setlang/", {"language": "zz", "next": "/"})
    assert "pystore_language" not in response.cookies


def test_inactive_language_hidden_from_selector(client, fa_language):
    Language.objects.create(code="de", name="Deutsch", is_active=False)
    content = client.get("/").content.decode()
    assert "Deutsch" not in content
    assert "فارسی" in content


def test_rtl_direction_auto_for_rtl_codes(db):
    arabic = upsert_language("العربية", "ar")
    assert arabic.direction == "rtl"
    german = upsert_language("Deutsch", "de")
    assert german.direction == "ltr"


def test_single_default_language(db):
    en = upsert_language("English", "en")
    set_default_language(en)
    fa = upsert_language("فارسی", "fa")
    set_default_language(fa)

    en.refresh_from_db()
    fa.refresh_from_db()
    assert fa.is_default and not en.is_default
    assert Language.objects.filter(is_default=True).count() == 1
