from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.cart.services import add_to_cart, get_or_create_cart
from apps.catalog.services import create_product, publish_product
from apps.checkout.models import PaymentMethod, ShippingMethod
from apps.cms.services import (
    add_menu_item,
    create_blog_post,
    create_page,
)
from apps.orders.models import Order
from apps.storefront.themes import (
    get_theme_config,
    get_theme_manifest,
    list_themes,
)
from apps.stores.services import create_store

User = get_user_model()

pytestmark = [pytest.mark.django_db]

PRICE = Decimal("100.0000")


@pytest.fixture
def store(db):
    return create_store("Storefront Store")


@pytest.fixture
def published_product(store):
    product = create_product(store, "Storefront Product", price=PRICE, stock_quantity=10)
    publish_product(product)
    return product


def test_theme_service_lists_and_reads_manifest():
    themes = list_themes()
    assert "default" in themes
    assert "alt-theme" in themes

    manifest = get_theme_manifest("default")
    assert manifest["name"] == "Default Theme"
    assert get_theme_config("default")["site_name"] == "pyStore"

    assert get_theme_manifest("missing-theme") == {}
    assert get_theme_config("missing-theme") == {}


def test_theme_config_for_alt_theme():
    assert get_theme_config("alt-theme")["site_name"] == "pyStore Alt"
    assert get_theme_config("alt-theme")["primary_color"] == "#c0392b"


def test_home_shows_published_products(client, store, published_product):
    response = client.get("/")
    assert response.status_code == 200
    content = response.content.decode()
    assert "Storefront Product" in content
    assert "theme-banner" in content


def test_theme_template_override_mechanism(client, store, settings):
    from django.test import override_settings

    alt_templates = str(settings.BASE_DIR / "themes" / "alt-theme" / "templates")
    templates = [dict(t) for t in settings.TEMPLATES]
    templates[0] = {**templates[0], "DIRS": [alt_templates]}

    with override_settings(TEMPLATES=templates, ACTIVE_THEME="alt-theme"):
        response = client.get("/")
        content = response.content.decode()
        assert "ALT THEME BANNER IS ACTIVE" in content


def test_theme_branding_in_base(client, settings, store):
    response = client.get("/")
    assert "pyStore" in response.content.decode()


def test_category_page_with_descendants(client, store, published_product):
    from apps.catalog.models import Category

    parent = Category.objects.create(name="Electronics", slug="electronics")
    child = Category.objects.create(name="Gadgets", slug="gadgets", parent=parent)
    published_product.category = child
    published_product.save()

    response = client.get("/category/electronics/")
    assert response.status_code == 200
    assert "Storefront Product" in response.content.decode()


def test_product_detail_page(client, store, published_product):
    response = client.get(f"/product/{published_product.slug}/")
    assert response.status_code == 200
    content = response.content.decode()
    assert "Storefront Product" in content
    assert "Add to cart" in content

    assert client.get("/product/does-not-exist/", {}).status_code == 404


def test_search_view(client, store, published_product):
    response = client.get("/search/", {"q": "Storefront"})
    assert "Storefront Product" in response.content.decode()

    empty = client.get("/search/", {"q": "zzzznothing"})
    assert "No results" in empty.content.decode()


def test_cart_page_with_session(client, store, published_product):
    response = client.get(f"/cart/add/{published_product.id}/")

    response = client.get("/cart/")
    assert response.status_code == 200
    assert "Storefront Product" in response.content.decode()
    assert "100.0000" in response.content.decode()


def test_checkout_page_and_flow(client, store, published_product, payment_methods=None):
    from apps.checkout.models import PaymentMethod, ShippingMethod

    ShippingMethod.objects.create(
        store=store, name="Post", code="POST", flat_price=Decimal("5.0000")
    )
    PaymentMethod.objects.create(name="COD", code="cash_on_delivery")

    session = client.session
    session.create()
    session.save()

    cart = get_or_create_cart(store, session_key=client.session.session_key)
    add_to_cart(cart, published_product, 2)

    page = client.get("/checkout/")
    assert page.status_code == 200

    response = client.post(
        "/checkout/",
        {
            "email": "guest@example.com",
            "country": "IR",
            "state": "TEH",
            "city": "Tehran",
            "address_line": "Test st",
            "shipping_method": "POST",
            "payment_method": "cash_on_delivery",
        },
    )
    assert response.status_code == 200
    assert Order.objects.filter(email="guest@example.com").exists()


def test_register_login_account_flow(client, store):
    response = client.post("/register/", {"email": "newuser@example.com", "password": "Str0ng!Passw0rd"})
    assert response.status_code == 302 or response.status_code == 200

    assert User.objects.filter(email="newuser@example.com").exists()

    client.post("/logout/")
    login_response = client.post("/login/", {"email": "newuser@example.com", "password": "Str0ng!Passw0rd"})
    assert login_response.status_code == 302

    account = client.get("/account/")
    assert account.status_code == 200
    assert "newuser@example.com" in account.content.decode()


def test_account_requires_login(client):
    response = client.get("/account/")
    assert response.status_code == 302


def test_wishlist_flow_in_views(client, store, published_product):
    client.post("/register/", {"email": "wishuser@example.com", "password": "Str0ng!Passw0rd"})

    client.get(f"/wishlist/add/{published_product.id}/")
    response = client.get("/wishlist/")
    assert "Storefront Product" in response.content.decode()

    client.get(f"/wishlist/move/{published_product.id}/")
    assert client.get("/wishlist/").content.decode().count("Storefront Product") == 0


def test_compare_flow_in_views(client, store, published_product):
    client.post("/register/", {"email": "cmpuser@example.com", "password": "Str0ng!Passw0rd"})
    client.get(f"/compare/add/{published_product.id}/")
    assert "Storefront Product" in client.get("/compare/").content.decode()
    client.get(f"/compare/remove/{published_product.id}/")
    assert "Storefront Product" not in client.get("/compare/").content.decode()


def test_order_detail_access_control(client, store, user_factory=None):
    from apps.cart.services import add_to_cart, get_or_create_cart
    from apps.checkout.services import execute_checkout

    ShippingMethod.objects.create(store=store, name="Post", code="POST", flat_price=0)
    PaymentMethod.objects.create(name="COD", code="cash_on_delivery")

    owner = User.objects.create_user(email="owner@example.com", password="Str0ng!Passw0rd")
    other = User.objects.create_user(email="other@example.com", password="Str0ng!Passw0rd")

    product = create_product(store, "Owned Product", price=PRICE, stock_quantity=5)
    publish_product(product)
    cart = get_or_create_cart(store, user=owner)
    add_to_cart(cart, product, 1)
    order = execute_checkout(
        cart, user=owner, shipping_address={"country": "IR", "city": "Tehran", "address_line": "x"},
        shipping_method_code="POST", payment_method_code="cash_on_delivery",
    )

    client.force_login(other)
    assert client.get(f"/orders/{order.number}/").status_code == 404

    client.force_login(owner)
    assert client.get(f"/orders/{order.number}/").status_code == 200


def test_cms_page_and_blog_views(client, store):
    page = create_page("About Shop", content="We are the shop")
    page.is_published = True
    page.save()

    create_blog_post("Blog Post One", content="Post body")

    assert "We are the shop" in client.get("/about-shop/").content.decode()
    assert client.get("/missing-page/").status_code == 404

    blog = client.get("/blog/")
    assert "Blog Post One" in blog.content.decode()
    assert "Post body" in client.get("/blog/blog-post-one/").content.decode()


def test_robots_and_sitemap_views(client, store):
    page = create_page("Sitemap Page")
    page.is_published = True
    page.save()

    robots = client.get("/robots.txt")
    assert robots["Content-Type"] == "text/plain"
    assert "Sitemap:" in robots.content.decode()

    sitemap = client.get("/sitemap.xml")
    assert sitemap["Content-Type"] == "application/xml"
    assert "sitemap-page" in sitemap.content.decode()


def test_context_processor_menu_and_branding(client, store):
    from apps.cms.models import Menu

    menu = Menu.objects.get_or_create(name="Main Menu", slug="main")[0]
    add_menu_item(menu, "Shop", url="/")

    response = client.get("/")
    content = response.content.decode()
    assert "pyStore" in content
    assert ">Shop</a>" in content


def test_storefront_app_registered(db):
    from django.apps import apps

    assert apps.is_installed("apps.storefront")
