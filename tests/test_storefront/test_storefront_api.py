import pytest
from django.contrib.auth import get_user_model
from django.test import Client, override_settings
from rest_framework.test import APIClient

from apps.catalog.services import create_product, publish_product
from apps.cms.models import Menu
from apps.cms.services import add_menu_item, create_blog_post, create_page
from apps.stores.services import ensure_default_store
from core.plugins.manager import PluginManager

User = get_user_model()

pytestmark = [pytest.mark.django_db]

PASSWORD = "Str0ng!Passw0rd"


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def store(db):
    return ensure_default_store("SPA Store")


@pytest.fixture
def published_product(store):
    product = create_product(store, "SPA Product", price=100, stock_quantity=5)
    publish_product(product)
    return product


@pytest.fixture
def auth_client(db):
    user = User.objects.create_user(email="spa@example.com", password=PASSWORD)
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def test_bootstrap_returns_theme_and_branding(api_client, store):
    response = api_client.get("/api/v1/storefront/bootstrap")
    assert response.status_code == 200
    assert response.data["theme"]["name"] == "default"
    assert response.data["branding"]["site_name"] == "pyStore"
    assert response.data["user"]["is_authenticated"] is False
    assert "languages" in response.data


def test_bootstrap_includes_menu_items(api_client, store):
    menu = Menu.objects.get_or_create(name="Main Menu", slug="main")[0]
    add_menu_item(menu, "Shop", url="/")

    response = api_client.get("/api/v1/storefront/bootstrap")
    titles = [item["title"] for item in response.data["menu"]]
    assert "Shop" in titles


def test_bootstrap_includes_currencies_with_irt_default(api_client, store):
    response = api_client.get("/api/v1/storefront/bootstrap")
    codes = [currency["code"] for currency in response.data["currencies"]]
    assert "IRT" in codes
    assert response.data["active_currency"]["code"] == "IRT"


def test_storefront_renders_currency_switcher(client, store):
    content = client.get("/").content.decode()
    assert "/i18n/setcurrency/" in content
    assert "IRT" in content


def test_set_currency_view_sets_cookie(client, store):
    response = client.post("/i18n/setcurrency/", {"currency": "USD", "next": "/"})
    assert response.status_code == 302
    assert response.cookies["pystore_currency"].value == "USD"


def test_hooks_endpoint_returns_plugin_fragments(api_client, store):
    manager = PluginManager()
    manager.discover_plugins()
    manager.install_plugin("slider")
    manager.enable_plugin("slider")

    response = api_client.get("/api/v1/storefront/hooks/home_middle")
    assert response.status_code == 200
    assert response.data["hook"] == "home_middle"
    assert any("pslider" in fragment["html"] for fragment in response.data["fragments"])


def test_hooks_endpoint_empty_without_plugins(api_client, store):
    response = api_client.get("/api/v1/storefront/hooks/home_middle")
    assert response.status_code == 200
    assert response.data["fragments"] == []


def test_search_endpoint_returns_products(api_client, store, published_product):
    response = api_client.get("/api/v1/storefront/search", {"q": "SPA"})
    assert response.status_code == 200
    slugs = [item["slug"] for item in response.data["results"]]
    assert published_product.slug in slugs


def test_page_and_blog_endpoints(api_client, store):
    page = create_page("About SPA", content="Body text")
    page.is_published = True
    page.save()
    post = create_blog_post("SPA Post", content="Post body")
    post.is_published = True
    post.save()

    page_response = api_client.get(f"/api/v1/storefront/pages/{page.slug}")
    assert page_response.status_code == 200
    assert page_response.data["content"] == "Body text"

    blog_response = api_client.get("/api/v1/storefront/blog")
    assert blog_response.status_code == 200
    assert any(item["slug"] == post.slug for item in blog_response.data)


def test_page_endpoint_404_for_unknown(api_client, store):
    assert api_client.get("/api/v1/storefront/pages/missing").status_code == 404


def test_wishlist_requires_authentication(api_client, store):
    assert api_client.get("/api/v1/storefront/wishlist").status_code in (401, 403)


def test_wishlist_add_and_remove(auth_client, store, published_product):
    add_response = auth_client.post(
        "/api/v1/storefront/wishlist", {"product": published_product.slug}, format="json"
    )
    assert add_response.status_code == 200
    assert len(add_response.data) == 1

    remove_response = auth_client.delete(f"/api/v1/storefront/wishlist/{published_product.id}")
    assert remove_response.status_code == 200
    assert remove_response.data == []


def test_compare_uses_guest_session_header(api_client, store, published_product):
    client = APIClient()
    client.credentials(HTTP_X_CART_SESSION="guest-session-1")

    add_response = client.post(
        "/api/v1/storefront/compare", {"product": published_product.slug}, format="json"
    )
    assert add_response.status_code == 200
    assert len(add_response.data) == 1

    list_response = client.get("/api/v1/storefront/compare")
    assert len(list_response.data) == 1


def test_spa_disabled_serves_server_rendered_storefront(store, published_product):
    response = Client().get("/")
    assert response.status_code == 200
    assert "SPA Product" in response.content.decode()


def test_spa_enabled_without_build_returns_instructions(store, tmp_path):
    with override_settings(
        STOREFRONT_SPA_ENABLED=True, STOREFRONT_SPA_DIR=str(tmp_path / "missing")
    ):
        response = Client().get("/cart/")
    assert response.status_code == 503
    assert "not built" in response.content.decode().lower()


def test_spa_enabled_serves_built_index_for_interactive_routes(store, tmp_path):
    (tmp_path / "index.html").write_text("<div id='app'>SPA SHELL</div>", encoding="utf-8")
    with override_settings(STOREFRONT_SPA_ENABLED=True, STOREFRONT_SPA_DIR=str(tmp_path)):
        response = Client().get("/cart/")
    assert response.status_code == 200
    assert "SPA SHELL" in response.content.decode()


def test_content_pages_stay_server_rendered_when_spa_enabled(store, published_product):
    with override_settings(STOREFRONT_SPA_ENABLED=True):
        response = Client().get("/")
    assert response.status_code == 200
    assert "SPA Product" in response.content.decode()
    assert "SPA SHELL" not in response.content.decode()


def test_api_login_establishes_session_for_ssr_pages(api_client, store):
    User.objects.create_user(email="session@example.com", password=PASSWORD)
    response = api_client.post(
        "/api/v1/auth/login", {"email": "session@example.com", "password": PASSWORD}
    )
    assert response.status_code == 200

    home = api_client.get("/")
    assert home.status_code == 200
    assert "Logout" in home.content.decode()


def test_cart_is_shared_between_ssr_actions_and_api(store, published_product):
    client = Client()
    client.get(f"/cart/add/{published_product.id}/")

    response = client.get("/api/v1/cart")
    assert response.status_code == 200
    assert len(response.json()["lines"]) == 1
