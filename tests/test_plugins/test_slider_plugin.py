import pytest
from django.contrib.auth import get_user_model

from apps.stores.services import create_store
from core.plugins.manager import PluginManager
from core.plugins.models import PluginState

User = get_user_model()

pytestmark = [pytest.mark.django_db]


@pytest.fixture
def store(db):
    return create_store("Slider Store")


@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser(email="root-slider@example.com", password="Str0ng!Passw0rd")


@pytest.fixture
def limited_staff(db):
    return User.objects.create_user(
        email="slider-staff@example.com",
        password="Str0ng!Passw0rd",
        user_type="staff",
        is_staff=True,
    )


@pytest.fixture
def enabled_slider(db):
    manager = PluginManager()
    manager.discover_plugins()
    manager.install_plugin("slider")
    manager.enable_plugin("slider")
    return manager


def test_slider_renders_on_home_when_enabled(client, store, enabled_slider):
    response = client.get("/")
    content = response.content.decode()
    assert "pslider" in content
    assert "pslider-slide" in content
    assert "/static/slider/img/slide1.svg" in content
    assert "/static/slider/css/slider.css" in content
    assert "/static/slider/js/slider.js" in content
    assert content.count("pslider-caption") >= 3


def test_slider_hidden_when_not_enabled(client, store):
    content = client.get("/").content.decode()
    assert "pslider" not in content


def test_home_renders_with_non_hook_plugin_enabled(client, store, db):
    """Regression: enabled plugins without storefront hooks (e.g. theme_pacific)
    must not break the home page hook rendering."""
    manager = PluginManager()
    manager.discover_plugins()
    manager.install_plugin("theme_pacific")
    manager.enable_plugin("theme_pacific")

    response = client.get("/")
    assert response.status_code == 200
    assert "pslider" not in response.content.decode()


def test_home_renders_with_broken_hook_plugin_enabled(client, store, db):
    """A plugin whose hook method raises must be skipped, not crash the page."""
    import json
    import shutil

    manager = PluginManager()
    manager.discover_plugins()

    broken = manager.plugins_dir / "zz_broken_hook"
    broken.mkdir(parents=True, exist_ok=True)
    try:
        (broken / "plugin.json").write_text(
            json.dumps(
                {
                    "id": "zz_broken_hook",
                    "name": "Broken Hook",
                    "version": "1.0.0",
                    "entry_point": "plugin:Plugin",
                }
            ),
            encoding="utf-8",
        )
        (broken / "plugin.py").write_text(
            "from core.plugins.base import Plugin as Base\n"
            "class Plugin(Base):\n"
            "    def get_storefront_hooks(self):\n"
            "        raise RuntimeError('boom')\n",
            encoding="utf-8",
        )
        manager.discover_plugins()
        manager.install_plugin("zz_broken_hook")
        manager.enable_plugin("zz_broken_hook")

        response = client.get("/")
        assert response.status_code == 200
    finally:
        shutil.rmtree(broken, ignore_errors=True)


def test_slider_renders_plugin_settings(client, store, enabled_slider):
    enabled_slider.set_settings(
        "slider",
        {
            "images": "/static/slider/img/slide2.svg | One slide only",
            "height": 220,
            "autoplay_ms": 0,
            "show_arrows": False,
            "show_indicators": True,
        },
    )

    content = client.get("/").content.decode()
    assert "--pslider-h: 220px" in content
    assert content.count("pslider-slide") == 1
    assert "One slide only" in content
    assert "pslider-arrow" not in content
    assert 'data-autoplay="0"' in content


def test_slider_settings_page_in_admin_sidebar(client, admin_user, enabled_slider):
    client.force_login(admin_user)
    content = client.get("/admin/").content.decode()
    assert "Plugin settings" in content
    assert 'href="/admin/plugins/slider/settings/"' in content


def test_slider_settings_page_save(client, admin_user, enabled_slider):
    client.force_login(admin_user)
    response = client.get("/admin/plugins/slider/settings/")
    assert response.status_code == 200
    assert "Slide images" in response.content.decode()

    response = client.post(
        "/admin/plugins/slider/settings/",
        {
            "images": "/static/slider/img/slide3.svg | Saved caption",
            "autoplay_ms": "2500",
            "height": "300",
            "show_arrows": "on",
            "show_indicators": "on",
        },
        follow=True,
    )
    assert "saved" in response.content.decode()

    state = PluginState.objects.get(plugin_id="slider")
    assert state.settings["autoplay_ms"] == 2500
    assert state.settings["height"] == 300
    assert state.settings["show_arrows"] is True
    assert "slide3.svg" in state.settings["images"]


def test_slider_settings_save_blocked_for_non_superuser(client, limited_staff, enabled_slider):
    client.force_login(limited_staff)
    response = client.post(
        "/admin/plugins/slider/settings/",
        {"images": "hack", "autoplay_ms": "1", "height": "1"},
        follow=True,
    )
    assert "Only superusers" in response.content.decode()
    state = PluginState.objects.get(plugin_id="slider")
    assert state.settings.get("images") != "hack"


def test_slider_settings_absent_when_disabled(client, admin_user, db):
    PluginManager().discover_plugins()
    client.force_login(admin_user)
    content = client.get("/admin/").content.decode()
    assert "Plugin settings" not in content


def test_pacific_theme_plugin_exposes_settings_schema(client, admin_user, db):
    manager = PluginManager()
    manager.discover_plugins()
    manager.install_plugin("theme_pacific")

    client.force_login(admin_user)
    response = client.get("/admin/plugins/theme_pacific/settings/")
    assert response.status_code == 200
    assert "Announcement bar text" in response.content.decode()

    client.post(
        "/admin/plugins/theme_pacific/settings/",
        {
            "announcement_text": "Custom announcement",
            "hero_title": "Custom hero",
            "hero_subtitle": "Custom subtitle",
            "footer_about": "Custom footer",
            "primary_color": "#123456",
            "accent_color": "#654321",
        },
    )
    state = PluginState.objects.get(plugin_id="theme_pacific")
    assert state.settings["hero_title"] == "Custom hero"


def test_plugins_page_lists_themes_and_settings_button(client, admin_user, enabled_slider):
    client.force_login(admin_user)
    content = client.get("/admin/plugins/").content.decode()
    assert "Themes" in content
    assert "Pacific" in content
    assert 'href="/admin/plugins/slider/settings/"' in content
