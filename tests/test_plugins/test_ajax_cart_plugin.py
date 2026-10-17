import json
import shutil

import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings

from apps.catalog.services import create_product, publish_product
from apps.stores.services import ensure_default_store
from core.plugins.manager import PluginManager
from core.plugins.models import PluginState

User = get_user_model()

pytestmark = [pytest.mark.django_db]


@pytest.fixture
def store(db):
    # The DRF cart API resolves the *default* store, so tests must use it too.
    return ensure_default_store("AjaxCart Store")


@pytest.fixture
def published_product(store):
    product = create_product(store, "Ajax Cart Product", price=100, stock_quantity=5)
    publish_product(product)
    return product


@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser(
        email="root-ajax-cart@example.com", password="Str0ng!Passw0rd"
    )


@pytest.fixture
def enabled_ajax_cart(db):
    manager = PluginManager()
    manager.discover_plugins()
    manager.install_plugin("ajax_cart")
    manager.enable_plugin("ajax_cart")
    return manager


def test_plugin_discovery_and_enable(db):
    manager = PluginManager()
    ids = manager.discover_plugins()
    assert "ajax_cart" in ids

    manager.install_plugin("ajax_cart")
    manager.enable_plugin("ajax_cart")
    state = PluginState.objects.get(plugin_id="ajax_cart")
    assert state.status == "enabled"


def test_hooks_render_when_enabled(client, store, enabled_ajax_cart):
    content = client.get("/").content.decode()
    assert "admin_panel/vendor/bootstrap/bootstrap.min.css" in content
    assert "ajax_cart/css/ajax_cart.css" in content
    assert "admin_panel/vendor/bootstrap/bootstrap.bundle.min.js" in content
    assert "ajax_cart/js/ajax_cart.js" in content
    assert 'id="ajaxCartDrawer"' in content
    assert "data-ajax-cart" in content
    assert "ajax-cart-button" in content
    assert "ajax-cart-badge" in content


def test_drawer_exposes_currency_and_settings(client, store, enabled_ajax_cart):
    content = client.get("/").content.decode()
    assert 'data-ajax-cart-currency="IRT"' in content
    assert 'data-ajax-cart-decimals="0"' in content
    assert "data-ajax-cart-coupon-form" in content
    assert "data-ajax-cart-lines" in content


def test_hooks_absent_when_disabled(client, store):
    content = client.get("/").content.decode()
    assert "ajax_cart" not in content
    assert "ajaxCartDrawer" not in content


def test_drawer_root_has_no_render_target_attributes(client, store, enabled_ajax_cart):
    """The offcanvas root must not reuse a client render-target attribute.

    ``ajax_cart.js`` toggles ``hidden`` on ``[data-ajax-cart-empty]`` and
    ``[data-ajax-cart-content]``. If the drawer root carried one of those
    attributes (as its config value), ``render()`` would hide the panel itself
    while the Bootstrap backdrop stayed visible: the page darkens but the
    drawer never appears. The empty-message config must use a distinct name.
    """
    content = client.get("/").content.decode()
    assert 'data-ajax-cart-empty-message="' in content
    assert 'data-ajax-cart-empty="' not in content
    assert "data-ajax-cart-content" not in content.split('id="ajaxCartDrawer"', 1)[1].split(">", 1)[0]


def test_product_buy_form_exposes_slug(client, store, published_product):
    content = client.get(f"/product/{published_product.slug}/").content.decode()
    assert "product-action product-buy" in content
    assert f'data-product-slug="{published_product.slug}"' in content


def test_plugin_cart_page_when_enabled_spa_disabled(client, store, enabled_ajax_cart):
    with override_settings(STOREFRONT_SPA_ENABLED=False):
        content = client.get("/cart/").content.decode()
    assert "ajax-cart-page" in content
    assert 'class="cart-page"' not in content


def test_default_cart_page_when_disabled(client, store):
    with override_settings(STOREFRONT_SPA_ENABLED=False):
        content = client.get("/cart/").content.decode()
    assert 'class="cart-page"' in content
    assert "ajax-cart-page" not in content


def test_cart_route_bypasses_spa_when_enabled(client, store, enabled_ajax_cart, tmp_path):
    (tmp_path / "index.html").write_text("<div id='app'>SPA SHELL</div>", encoding="utf-8")
    with override_settings(STOREFRONT_SPA_ENABLED=True, STOREFRONT_SPA_DIR=str(tmp_path)):
        content = client.get("/cart/").content.decode()
    assert "ajax-cart-page" in content
    assert "SPA SHELL" not in content


def test_cart_route_uses_spa_when_disabled(client, store, tmp_path):
    (tmp_path / "index.html").write_text("<div id='app'>SPA SHELL</div>", encoding="utf-8")
    with override_settings(STOREFRONT_SPA_ENABLED=True, STOREFRONT_SPA_DIR=str(tmp_path)):
        content = client.get("/cart/").content.decode()
    assert "SPA SHELL" in content
    assert "ajax-cart-page" not in content


def test_broken_hook_plugin_does_not_claim_cart_route(client, store, tmp_path):
    """A plugin whose hook method raises must not break or claim /cart/."""
    manager = PluginManager()
    manager.discover_plugins()

    broken = manager.plugins_dir / "zz_broken_cart"
    broken.mkdir(parents=True, exist_ok=True)
    try:
        (broken / "plugin.json").write_text(
            json.dumps(
                {
                    "id": "zz_broken_cart",
                    "name": "Broken Cart",
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
        manager.install_plugin("zz_broken_cart")
        manager.enable_plugin("zz_broken_cart")

        (tmp_path / "index.html").write_text("<div id='app'>SPA SHELL</div>", encoding="utf-8")
        with override_settings(STOREFRONT_SPA_ENABLED=True, STOREFRONT_SPA_DIR=str(tmp_path)):
            content = client.get("/cart/").content.decode()
        assert "SPA SHELL" in content
    finally:
        shutil.rmtree(broken, ignore_errors=True)


def test_cart_api_uses_default_store(client, store, published_product):
    response = client.post(
        "/api/v1/cart/items",
        data=json.dumps({"product": published_product.slug, "quantity": 2}),
        content_type="application/json",
    )
    assert response.status_code == 201
    body = response.json()
    assert len(body["lines"]) == 1
    assert body["lines"][0]["quantity"] == 2


def test_settings_page_in_admin_sidebar(client, admin_user, enabled_ajax_cart):
    client.force_login(admin_user)
    content = client.get("/admin/").content.decode()
    assert 'href="/admin/plugins/ajax_cart/settings/"' in content


def test_settings_page_renders_and_saves(client, admin_user, enabled_ajax_cart):
    client.force_login(admin_user)
    response = client.get("/admin/plugins/ajax_cart/settings/")
    assert response.status_code == 200
    assert "Empty cart message" in response.content.decode()

    response = client.post(
        "/admin/plugins/ajax_cart/settings/",
        {
            "open_drawer_on_add": "on",
            "show_header_badge": "on",
            "accent_color": "#123456",
            "free_shipping_threshold": "50",
            "empty_message": "Nothing here yet.",
            "checkout_label": "Pay now",
        },
        follow=True,
    )
    assert "saved" in response.content.decode()

    state = PluginState.objects.get(plugin_id="ajax_cart")
    assert state.settings["accent_color"] == "#123456"
    assert state.settings["empty_message"] == "Nothing here yet."
    assert state.settings["checkout_label"] == "Pay now"
    assert state.settings["open_drawer_on_add"] is True


def test_settings_absent_when_disabled(client, admin_user, db):
    PluginManager().discover_plugins()
    client.force_login(admin_user)
    content = client.get("/admin/").content.decode()
    assert 'href="/admin/plugins/ajax_cart/settings/"' not in content
