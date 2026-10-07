from datetime import timedelta
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.catalog.pricing import pricing_registry
from apps.catalog.services import create_product, publish_product
from apps.stores.services import create_store
from core.plugins.manager import PluginManager
from plugins.flash_sale.models import FlashSaleProduct
from plugins.flash_sale.services import create_flash_sale

User = get_user_model()

pytestmark = [pytest.mark.django_db]


@pytest.fixture
def store(db):
    return create_store("Flash Sale Store")


@pytest.fixture
def product(store, db):
    product = create_product(store, "Flash Product", price=Decimal("100.0000"), stock_quantity=50)
    publish_product(product)
    return product


@pytest.fixture
def enabled_plugin(db):
    manager = PluginManager()
    manager.discover_plugins()
    manager.install_plugin("flash_sale")
    manager.enable_plugin("flash_sale")
    return manager


def _window(start_offset_hours=-1, end_offset_hours=23):
    now = timezone.now()
    return now + timedelta(hours=start_offset_hours), now + timedelta(hours=end_offset_hours)


def test_price_modifier_applies_during_sale(product, enabled_plugin):
    start, end = _window()
    create_flash_sale(
        product.id, discount_percent=Decimal("25"), start_at=start, end_at=end, quantity=10
    )

    price = pricing_registry.resolve(product)
    assert price == Decimal("75.0000")


def test_price_modifier_ignored_outside_window(product, enabled_plugin):
    start, end = _window(start_offset_hours=48, end_offset_hours=72)
    create_flash_sale(
        product.id, discount_percent=Decimal("25"), start_at=start, end_at=end, quantity=10
    )

    assert pricing_registry.resolve(product) == Decimal("100.0000")


def test_price_modifier_ignored_when_sold_out(store, product, enabled_plugin):
    from apps.orders.models import Order, OrderItem

    start, end = _window()
    sale = create_flash_sale(
        product.id, discount_percent=Decimal("50"), start_at=start, end_at=end, quantity=1
    )

    order = Order.objects.create(number="FS-1", store=store, email="x@example.com")
    OrderItem.objects.create(
        order=order, product=product, product_name=product.name,
        quantity=2, unit_price=product.price, line_total=product.price * 2,
    )

    assert sale.remaining_quantity() == 0
    assert pricing_registry.resolve(product) == Decimal("100.0000")


def test_best_discount_wins_with_overlapping_sales(product, enabled_plugin):
    start, end = _window()
    create_flash_sale(product.id, discount_percent=Decimal("10"), start_at=start, end_at=end)
    create_flash_sale(product.id, discount_percent=Decimal("30"), start_at=start, end_at=end)

    assert pricing_registry.resolve(product) == Decimal("70.0000")


def test_flash_sale_admin_crud(client, admin_user, product, enabled_plugin):
    User.objects.create_superuser(email="fs-admin@example.com", password="Str0ng!Passw0rd")
    admin = User.objects.get(email="fs-admin@example.com")
    client.force_login(admin)

    response = client.get("/admin/plugins/flash_sale/flash-sale/")
    assert response.status_code == 200

    start = (timezone.now() - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M")
    end = (timezone.now() + timedelta(days=2)).strftime("%Y-%m-%dT%H:%M")
    response = client.post(
        "/admin/plugins/flash_sale/flash-sale/add/",
        {
            "product": product.id,
            "discount_percent": "20",
            "start_at": start,
            "end_at": end,
            "quantity": "5",
            "is_active": "on",
        },
        follow=True,
    )
    assert "Flash sale saved" in response.content.decode()
    sale = FlashSaleProduct.objects.get(product=product)
    assert sale.discount_percent == Decimal("20")

    response = client.post(
        f"/admin/plugins/flash_sale/flash-sale/{sale.id}/edit/",
        {
            "product": product.id,
            "discount_percent": "35",
            "start_at": start,
            "end_at": end,
            "quantity": "5",
            "is_active": "on",
        },
        follow=True,
    )
    assert "Flash sale saved" in response.content.decode()
    assert FlashSaleProduct.objects.get(pk=sale.id).discount_percent == Decimal("35")

    response = client.post(
        f"/admin/plugins/flash_sale/flash-sale/{sale.id}/delete/", follow=True
    )
    assert not FlashSaleProduct.objects.filter(pk=sale.id).exists()


def test_flash_sale_requires_admin_user(client, store, product, enabled_plugin):
    User.objects.create_user(email="fs-cust@example.com", password="Str0ng!Passw0rd")
    client.force_login(User.objects.get(email="fs-cust@example.com"))
    response = client.get("/admin/plugins/flash_sale/flash-sale/")
    assert response.status_code in (302, 403)


def test_home_shows_flash_sale_section(client, store, product, enabled_plugin):
    start, end = _window()
    create_flash_sale(
        product.id, discount_percent=Decimal("25"), start_at=start, end_at=end, quantity=10
    )

    content = client.get("/").content.decode()
    assert "flash-sale-card" in content
    assert "Flash Product" in content
    assert "75.0000" in content
    assert "10 left" in content


def test_home_hides_flash_sale_section_when_none(client, store, enabled_plugin):
    content = client.get("/").content.decode()
    assert "flash-sale-card" not in content


def test_sidebar_shows_flash_sale_manage_link(client, admin_user, enabled_plugin):
    client.force_login(admin_user)
    content = client.get("/admin/").content.decode()
    assert "Flash Sale — manage" in content
    assert 'href="/admin/plugins/flash_sale/flash-sale/"' in content
