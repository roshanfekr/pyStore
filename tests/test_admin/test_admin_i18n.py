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
