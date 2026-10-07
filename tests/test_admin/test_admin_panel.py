from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.cart.services import add_to_cart, get_or_create_cart
from apps.catalog.services import create_product, publish_product
from apps.checkout.models import ShippingMethod
from apps.checkout.services import execute_checkout
from apps.orders.models import Order, ReturnRequest
from apps.orders.services import request_return, set_payment_status, transition_order_status
from apps.pricing.models import Discount
from apps.stores.services import create_store

User = get_user_model()

pytestmark = [pytest.mark.django_db]

PRICE = Decimal("100.0000")
ADDRESS = {"country": "IR", "city": "Tehran", "address_line": "Admin test st"}


@pytest.fixture
def store(db):
    return create_store("Admin Store")


@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser(email="root@example.com", password="Str0ng!Passw0rd")


@pytest.fixture
def limited_staff(db):
    user = User.objects.create_user(
        email="staff@example.com", password="Str0ng!Passw0rd",
        user_type="staff", is_staff=True,
    )
    return user


@pytest.fixture
def shipping_method(db, store):
    return ShippingMethod.objects.create(
        store=store, name="Post", code="POST", flat_price=Decimal("5.0000")
    )


@pytest.fixture
def payment_methods(db):
    from apps.checkout.models import ensure_default_payment_methods

    ensure_default_payment_methods()


@pytest.fixture
def paid_order(store, db, shipping_method, payment_methods):
    customer = User.objects.create_user(email="omadmin@example.com", password="Str0ng!Passw0rd")
    product = create_product(store, "Admin Product", price=PRICE, stock_quantity=20)
    publish_product(product)
    cart = get_or_create_cart(store, user=customer)
    add_to_cart(cart, product, 2)
    order = execute_checkout(
        cart, user=customer, shipping_address=dict(ADDRESS),
        shipping_method_code="POST", payment_method_code="cash_on_delivery",
    )
    transition_order_status(order, Order.STATUS_PROCESSING)
    set_payment_status(order, Order.PAYMENT_PAID)
    transition_order_status(order, Order.STATUS_PAID)
    return order


def _action_post(client, model_changelist_path, action_name, pks, confirm=None):
    data = {"action": action_name, "_selected_action": [str(pk) for pk in pks]}
    if confirm:
        data["confirm"] = confirm
    return client.post(model_changelist_path, data, follow=True)


def test_dashboard_requires_staff(client, db):
    response = client.get("/admin/", follow=False)
    assert response.status_code == 302
    assert "/login" in response.url


def test_dashboard_shows_stats(client, admin_user, paid_order):
    client.force_login(admin_user)
    response = client.get("/admin/")
    content = response.content.decode()
    assert "pyStore Administration" in content
    assert "Low stock alerts" in content


def test_admin_sidebar_links_plugins_and_reports(client, admin_user):
    client.force_login(admin_user)
    for page in ("/admin/", "/admin/plugins/", "/admin/reports/"):
        response = client.get(page)
        content = response.content.decode()
        assert 'href="/admin/plugins/"' in content, f"Plugins sidebar link missing on {page}"
        assert 'href="/admin/reports/"' in content, f"Reports sidebar link missing on {page}"


def test_all_sections_load_for_superuser(client, admin_user, paid_order, store):
    client.force_login(admin_user)
    sections = [
        "/admin/catalog/product/",
        "/admin/catalog/category/",
        "/admin/catalog/brand/",
        "/admin/catalog/tag/",
        "/admin/inventory/warehouse/",
        "/admin/inventory/inventoryitem/",
        "/admin/inventory/inventorytransaction/",
        "/admin/identity/user/",
        "/admin/identity/customer/",
        "/admin/identity/role/",
        "/admin/identity/permission/",
        "/admin/orders/order/",
        "/admin/orders/orderitem/",
        "/admin/orders/refund/",
        "/admin/orders/returnrequest/",
        "/admin/orders/orderstatuslog/",
        "/admin/pricing/pricelist/",
        "/admin/pricing/discount/",
        "/admin/pricing/taxclass/",
        "/admin/pricing/taxrate/",
        "/admin/stores/store/",
        "/admin/vendors/vendor/",
        "/admin/checkout/shippingmethod/",
        "/admin/checkout/paymentmethod/",
        "/admin/cms/page/",
        "/admin/cms/blogpost/",
        "/admin/cms/menu/",
        "/admin/cms/widget/",
        "/admin/cms/contentblock/",
        "/admin/media/mediafile/",
        "/admin/cart/cart/",
        "/admin/core/pluginstate/",
    ]
    for path in sections:
        response = client.get(path)
        assert response.status_code == 200, f"Section {path} failed"


def test_order_search_and_filter(client, admin_user, paid_order):
    client.force_login(admin_user)

    response = client.get(f"/admin/orders/order/?q={paid_order.number}")
    assert paid_order.number in response.content.decode()

    filtered = client.get("/admin/orders/order/?status=paid")
    assert paid_order.number in filtered.content.decode()


def test_cancel_orders_action_requires_confirmation(client, admin_user, paid_order):
    client.force_login(admin_user)
    response = _action_post(client, "/admin/orders/order/", "cancel_orders", [paid_order.id])
    content = response.content.decode()
    assert "Cancel selected orders?" in content
    assert "cannot be undone" in content

    paid_order.refresh_from_db()
    assert paid_order.status != Order.STATUS_CANCELLED


def test_cancel_orders_confirmed(client, admin_user, paid_order):
    client.force_login(admin_user)
    response = _action_post(
        client, "/admin/orders/order/", "cancel_orders", [paid_order.id], confirm="yes"
    )

    paid_order.refresh_from_db()
    assert paid_order.status == Order.STATUS_CANCELLED
    assert "1 order(s) cancelled" in response.content.decode()


def test_cancel_orders_blocked_without_permission(client, limited_staff, paid_order):
    from django.contrib.auth.models import Permission as DjangoPermission

    change_perm = DjangoPermission.objects.get(
        codename="change_order", content_type__app_label="orders"
    )
    limited_staff.user_permissions.add(change_perm)

    client.force_login(limited_staff)
    response = _action_post(
        client, "/admin/orders/order/", "cancel_orders", [paid_order.id], confirm="yes"
    )

    paid_order.refresh_from_db()
    assert paid_order.status != Order.STATUS_CANCELLED
    assert "Permission denied" in response.content.decode()


def test_mark_shipped_action_with_confirmation(client, admin_user, paid_order):
    client.force_login(admin_user)
    _action_post(client, "/admin/orders/order/", "mark_shipped", [paid_order.id])

    _action_post(
        client, "/admin/orders/order/", "mark_shipped", [paid_order.id], confirm="yes"
    )
    paid_order.refresh_from_db()
    assert paid_order.status == Order.STATUS_SHIPPED
    assert paid_order.shipment_status == Order.SHIPMENT_SHIPPED


def test_product_bulk_publish_action(client, admin_user, store):
    client.force_login(admin_user)
    product = create_product(store, "Bulk Publish Product", price=PRICE)
    product2 = create_product(store, "Bulk Publish 2", price=PRICE)

    _action_post(client, "/admin/catalog/product/", "publish_products", [product.id, product2.id])

    product.refresh_from_db()
    product2.refresh_from_db()
    assert product.is_published and product2.is_published


def test_discount_bulk_actions(client, admin_user, store):
    discount = Discount.objects.create(
        name="Bulk Discount", discount_type="percentage", value=Decimal("10")
    )
    client.force_login(admin_user)
    _action_post(client, "/admin/pricing/discount/", "deactivate_discounts", [discount.id])
    discount.refresh_from_db()
    assert discount.is_active is False

    _action_post(client, "/admin/pricing/discount/", "activate_discounts", [discount.id])
    discount.refresh_from_db()
    assert discount.is_active is True


def test_return_request_actions(client, admin_user, paid_order):
    customer = User.objects.get(email="omadmin@example.com")
    item = paid_order.items.first()
    return_request = request_return(paid_order, [(item, 1)], user=customer, reason="testing")

    client.force_login(admin_user)
    _action_post(client, "/admin/orders/returnrequest/", "approve_requests", [return_request.id])
    return_request.refresh_from_db()
    assert return_request.status == ReturnRequest.STATUS_APPROVED

    _action_post(client, "/admin/orders/returnrequest/", "reject_requests", [return_request.id])
    return_request.refresh_from_db()
    assert return_request.status == ReturnRequest.STATUS_APPROVED


def test_reports_view(client, admin_user, paid_order):
    client.force_login(admin_user)
    response = client.get("/admin/reports/")
    content = response.content.decode()
    assert "Total revenue" in content
    assert "Orders by status" in content
    assert "Most used discounts" in content


def test_plugins_view_lists_plugins(client, admin_user):
    client.force_login(admin_user)
    response = client.get("/admin/plugins/")
    content = response.content.decode()
    assert "payment_dummy" in content
    assert "shipping_dummy" in content


def test_plugin_lifecycle_through_admin(client, admin_user, db):
    from core.plugins.models import PluginState

    client.force_login(admin_user)

    response = client.post(
        "/admin/plugins/", {"action": "install", "plugin_id": "payment_dummy"}, follow=True
    )
    assert "installed successfully" in response.content.decode()
    assert PluginState.objects.get(plugin_id="payment_dummy").status == "installed"

    client.post("/admin/plugins/", {"action": "enable", "plugin_id": "payment_dummy"})
    assert PluginState.objects.get(plugin_id="payment_dummy").status == "enabled"

    client.post("/admin/plugins/", {"action": "disable", "plugin_id": "payment_dummy"})
    assert PluginState.objects.get(plugin_id="payment_dummy").status == "disabled"

    client.post("/admin/plugins/", {"action": "uninstall", "plugin_id": "payment_dummy"}, follow=True)
    assert not PluginState.objects.filter(plugin_id="payment_dummy").exists()


def test_plugin_action_blocked_for_non_superuser(client, limited_staff):
    from core.plugins.models import PluginState

    client.force_login(limited_staff)
    response = client.post(
        "/admin/plugins/", {"action": "install", "plugin_id": "payment_dummy"}, follow=True
    )
    assert "Only superusers can manage plugins" in response.content.decode()
    assert not PluginState.objects.filter(plugin_id="payment_dummy").exists()


def test_uninstall_requires_disabled_plugin(client, admin_user, db):
    from core.plugins.models import PluginState

    client.force_login(admin_user)
    client.post("/admin/plugins/", {"action": "install", "plugin_id": "payment_dummy"})

    response = client.post(
        "/admin/plugins/", {"action": "uninstall", "plugin_id": "payment_dummy"}, follow=True
    )
    assert "must be disabled" in response.content.decode()
    assert PluginState.objects.filter(plugin_id="payment_dummy").exists()


def test_pagination_in_changelist(client, admin_user, store):
    client.force_login(admin_user)
    for index in range(15):
        product = create_product(store, f"Page Product {index}", price=PRICE)
        publish_product(product)

    response = client.get("/admin/catalog/product/?p=1")
    assert response.status_code == 200
    assert "Page Product" in response.content.decode()


def test_readonly_transaction_admin(client, admin_user, paid_order):
    client.force_login(admin_user)
    response = client.get("/admin/inventory/inventorytransaction/add/")
    assert response.status_code == 403 or response.status_code == 404
