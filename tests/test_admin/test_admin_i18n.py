from unittest import mock

import pytest
from django.contrib.auth import get_user_model

pytestmark = [pytest.mark.django_db]

User = get_user_model()


@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser(email="i18n-admin@example.com", password="Str0ng!Passw0rd")


@pytest.fixture
def fa_language(db):
    from apps.stores.models import Language
    from apps.stores.seed_translations import PERSIAN_STRINGS
    from apps.stores.services import seed_language_resources

    language, _ = Language.objects.get_or_create(
        code="fa",
        defaults={"name": "فارسی", "is_active": True, "direction": "rtl", "ordering": 1},
    )
    seed_language_resources("fa", PERSIAN_STRINGS)
    return language


def test_admin_header_has_language_switcher(client, admin_user, fa_language):
    client.force_login(admin_user)
    content = client.get("/admin/").content.decode()
    assert "/i18n/setlang/" in content
    assert 'name="language"' in content


def test_admin_dashboard_renders_persian(client, admin_user, fa_language):
    client.force_login(admin_user)
    client.cookies["pystore_language"] = "fa"
    content = client.get("/admin/").content.decode()
    assert "داشبورد" in content
    assert "کل سفارش‌ها" in content
    assert "هشدار کمبود موجودی" in content


def test_admin_sidebar_renders_persian(client, admin_user, fa_language):
    client.force_login(admin_user)
    client.cookies["pystore_language"] = "fa"
    content = client.get("/admin/").content.decode()
    assert "مرور کلی" in content
    assert "تنظیمات پلاگین‌ها" not in content  # no enabled plugins with pages


def test_plugins_page_renders_persian(client, admin_user, fa_language):
    client.force_login(admin_user)
    client.cookies["pystore_language"] = "fa"
    content = client.get("/admin/plugins/").content.decode()
    assert "قالب‌ها" in content
    assert "نامک" in content
    assert "درگاه‌های پرداخت ثبت‌شده" in content


def test_flash_sale_admin_renders_persian(client, admin_user, fa_language):
    from core.plugins.manager import PluginManager

    manager = PluginManager()
    manager.discover_plugins()
    manager.install_plugin("flash_sale")
    manager.enable_plugin("flash_sale")

    client.force_login(admin_user)
    client.cookies["pystore_language"] = "fa"
    content = client.get("/admin/plugins/flash_sale/flash-sale/").content.decode()
    assert "فروش‌های ویژه" in content
    assert "افزودن فروش ویژه" in content


def test_admin_switch_to_english(client, admin_user, fa_language):
    client.force_login(admin_user)
    client.cookies["pystore_language"] = "en"
    content = client.get("/admin/").content.decode()
    assert "Dashboard" in content


@pytest.fixture
def product(db):
    from apps.catalog.services import create_product
    from apps.stores.services import create_store

    store = create_store("I18n Store")
    return create_product(store, "I18n Product", price="10.00")


def test_product_definition_labels_render_persian(client, admin_user, fa_language, product):
    client.force_login(admin_user)
    client.cookies["pystore_language"] = "fa"
    content = client.get(f"/admin/catalog/product/{product.pk}/change/").content.decode()
    # Unique namespaced keys resolve to Persian field labels.
    assert "نام محصول" in content
    assert "قیمت پیش از تخفیف" in content
    assert "برچسب‌ها" in content
    assert "دوره پرداخت تکرارشونده" in content


def test_product_inline_titles_render_persian(client, admin_user, fa_language, product):
    client.force_login(admin_user)
    client.cookies["pystore_language"] = "fa"
    content = client.get(f"/admin/catalog/product/{product.pk}/change/").content.decode()
    assert "گونه‌های محصول" in content
    assert "مشخصات محصول" in content
    assert "تنظیمات سئوی محصول" in content


def test_product_image_dialog_labels_render_persian(client, admin_user, fa_language, product):
    client.force_login(admin_user)
    client.cookies["pystore_language"] = "fa"
    content = client.get(f"/admin/catalog/product/{product.pk}/change/").content.decode()
    assert "مدیریت تصاویر" in content
    assert "متن جایگزین" in content


def test_product_inline_dialog_controls_render_persian(client, admin_user, fa_language, product):
    client.force_login(admin_user)
    client.cookies["pystore_language"] = "fa"
    content = client.get(f"/admin/catalog/product/{product.pk}/change/").content.decode()
    # Grid + modal controls for the dialog-based inlines.
    assert "افزودن" in content
    assert "ویرایش" in content
    assert "عملیات" in content


def test_product_definition_never_leaks_raw_keys(client, admin_user, fa_language, product):
    client.force_login(admin_user)
    client.cookies["pystore_language"] = "fa"
    content = client.get(f"/admin/catalog/product/{product.pk}/change/").content.decode()
    assert "admin.form.catalog.product." not in content
    assert "admin.inline.catalog." not in content
    assert "admin.image." not in content


def test_product_definition_falls_back_to_english_without_translation(
    client, admin_user, product
):
    # No ``fa`` resources seeded and the cookie points at English: labels must
    # keep their original English text instead of showing raw namespaced keys.
    client.force_login(admin_user)
    client.cookies["pystore_language"] = "en"
    content = client.get(f"/admin/catalog/product/{product.pk}/change/").content.decode()
    assert "admin.form.catalog.product." not in content
    assert "Name" in content


def test_lookup_optional_tolerates_missing_catalog(db):
    # On a fresh (unmigrated) database the ``LocaleStringResource`` table does
    # not exist yet. The lookup must fall back to ``None`` (original label)
    # instead of raising, so management commands can bootstrap the database.
    from django.db import OperationalError

    from apps.admin_panel import i18n as admin_i18n

    with mock.patch.object(
        admin_i18n, "_catalog_for", side_effect=OperationalError("no such table")
    ):
        assert admin_i18n._lookup_optional("admin.form.catalog.product.name") is None


def test_admin_system_checks_survive_fresh_database(db):
    # Django's admin system check instantiates every inline class
    # (``inline(obj.model, obj.admin_site).check()``). With the catalog
    # unavailable, instantiation must not raise — this is exactly the path
    # that broke ``migrate`` / ``makemigrations`` on a fresh database.
    from django.core.management import call_command
    from django.db import OperationalError

    from apps.admin_panel import i18n as admin_i18n

    with mock.patch.object(
        admin_i18n, "_catalog_for", side_effect=OperationalError("no such table")
    ):
        call_command("check")
