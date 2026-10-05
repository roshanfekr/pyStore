from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.catalog.services import add_variant, create_product
from apps.inventory.models import InventoryTransaction
from apps.inventory.services import (
    add_warehouse_location,
    adjust_stock,
    consume_stock,
    create_warehouse,
    ensure_inventory_permissions,
    get_or_create_inventory,
    inventory_for_variant,
    receive_stock,
    release_stock,
    reserve_stock,
    transfer_stock,
)
from apps.stores.services import create_store
from core.events import dispatcher
from core.exceptions import ConflictError, ValidationError

User = get_user_model()

pytestmark = [pytest.mark.django_db]


@pytest.fixture
def store(db):
    return create_store("Inventory Store")


@pytest.fixture
def warehouse(db, store):
    return create_warehouse(store, "Main Warehouse", "WH-1", city="Tehran", country="IR")


@pytest.fixture
def user(db):
    return User.objects.create_user(email="keeper@example.com", password="Str0ng!Passw0rd")


@pytest.fixture
def variant_item(db, store, warehouse):
    product = create_product(store, "Warehouse Shirt", product_type="variant")
    variant = add_variant(product, "INV-SHIRT-M", Decimal("25.0000"))
    return get_or_create_inventory(warehouse, variant=variant, low_stock_threshold=3)


def test_create_warehouse_unique_code(store, warehouse):
    assert warehouse.code == "WH-1"
    with pytest.raises(ConflictError):
        create_warehouse(store, "Another", "WH-1")


def test_warehouse_location_unique(warehouse):
    add_warehouse_location(warehouse, "A-01")
    with pytest.raises(ConflictError):
        add_warehouse_location(warehouse, "A-01")


def test_inventory_requires_exactly_one_target(warehouse, store):
    product = create_product(store, "X", product_type="variant")
    variant = add_variant(product, "XOR-1", Decimal("1.0000"))
    with pytest.raises(ValidationError):
        get_or_create_inventory(warehouse, product=product, variant=variant)
    with pytest.raises(ValidationError):
        get_or_create_inventory(warehouse)
    item = get_or_create_inventory(warehouse, product=product)
    assert item.product_id == product.id


def test_receive_stock_with_audit(variant_item, user):
    receive_stock(variant_item, 50, actor=user, reference="PO-1001")

    variant_item.refresh_from_db()
    assert variant_item.stock_quantity == 50
    assert variant_item.available_quantity == 50

    tx = InventoryTransaction.objects.get(inventory_item=variant_item)
    assert tx.transaction_type == "receive"
    assert tx.stock_delta == 50
    assert tx.resulting_stock == 50
    assert tx.actor_id == user.id
    assert tx.reference == "PO-1001"


def test_receive_rejects_non_positive(variant_item):
    with pytest.raises(ValidationError):
        receive_stock(variant_item, 0)


def test_adjust_stock_up_and_down(variant_item, user):
    adjust_stock(variant_item, 10, actor=user)
    adjust_stock(variant_item, -4, actor=user)
    variant_item.refresh_from_db()
    assert variant_item.stock_quantity == 6


def test_adjust_rejects_negative_result(variant_item):
    with pytest.raises(ConflictError):
        adjust_stock(variant_item, -5)


def test_reserve_and_release(variant_item, user):
    receive_stock(variant_item, 10)

    reserve_stock(variant_item, 4, actor=user, reference="ORDER-1")
    variant_item.refresh_from_db()
    assert variant_item.reserved_quantity == 4
    assert variant_item.available_quantity == 6

    release_stock(variant_item, 4, actor=user, reference="ORDER-1-cancel")
    variant_item.refresh_from_db()
    assert variant_item.reserved_quantity == 0
    assert variant_item.available_quantity == 10


def test_reserve_overselling_rejected_without_backorder(variant_item, user):
    receive_stock(variant_item, 3)
    with pytest.raises(ConflictError, match="available"):
        reserve_stock(variant_item, 5, actor=user)


def test_reserve_with_backorder_allows_oversell(store, warehouse, user):
    product = create_product(store, "Backorderable", product_type="variant")
    variant = add_variant(product, "BO-1", Decimal("9.0000"))
    item = get_or_create_inventory(warehouse, variant=variant, backorder_allowed=True)

    reserve_stock(item, 5, actor=user)
    item.refresh_from_db()
    assert item.reserved_quantity == 5
    assert item.stock_quantity == 0
    assert item.is_backordered is True
    assert item.stock_status == "out_of_stock"


def test_release_more_than_reserved_rejected(variant_item, user):
    receive_stock(variant_item, 10)
    reserve_stock(variant_item, 2)
    with pytest.raises(ConflictError):
        release_stock(variant_item, 3)


def test_consume_stock_fulfills_reservation(variant_item, user):
    receive_stock(variant_item, 10)
    reserve_stock(variant_item, 4, reference="ORDER-9")

    consume_stock(variant_item, 4, actor=user, reference="SHIP-9")

    variant_item.refresh_from_db()
    assert variant_item.stock_quantity == 6
    assert variant_item.reserved_quantity == 0
    assert variant_item.available_quantity == 6


def test_consume_more_than_stock_rejected(variant_item, user):
    receive_stock(variant_item, 2)
    reserve_stock(variant_item, 2)
    with pytest.raises(ConflictError):
        consume_stock(variant_item, 5)


def test_stock_status_levels(store, warehouse):
    product = create_product(store, "Status Product", price=Decimal("5.0000"))
    item = get_or_create_inventory(warehouse, product=product, low_stock_threshold=5)

    item = receive_stock(item, 10)
    assert item.stock_status == "in_stock"

    item = adjust_stock(item, -6)
    assert item.available_quantity == 4
    assert item.stock_status == "low_stock"

    item = adjust_stock(item, -4)
    assert item.stock_status == "out_of_stock"


def test_low_stock_event_dispatched(store, warehouse):
    received = []
    from apps.inventory.events import InventoryLowStock

    def handler(event):
        received.append(event)

    dispatcher.subscribe(InventoryLowStock, handler)
    try:
        product = create_product(store, "Low Product", price=Decimal("5.0000"))
        item = get_or_create_inventory(warehouse, product=product, low_stock_threshold=5)
        receive_stock(item, 4)
    finally:
        dispatcher.unsubscribe(InventoryLowStock, handler)

    assert len(received) == 1
    assert received[0].available_quantity == 4


def test_transfer_between_warehouses(store, warehouse, user):
    other = create_warehouse(store, "Second Warehouse", "WH-2")
    product = create_product(store, "Transferable", price=Decimal("5.0000"))
    item = get_or_create_inventory(warehouse, product=product)

    receive_stock(item, 20)
    source_item, target_item = transfer_stock(item, other, 8, actor=user, reference="TRF-1")

    source_item.refresh_from_db()
    target_item.refresh_from_db()
    assert source_item.stock_quantity == 12
    assert target_item.stock_quantity == 8

    types = set(
        InventoryTransaction.objects.filter(
            inventory_item__in=[source_item, target_item]
        ).values_list("transaction_type", flat=True)
    )
    assert {"transfer_out", "transfer_in"} <= types


def test_transfer_to_same_warehouse_rejected(warehouse):
    product = create_product(
        create_store("T Store"), "Same WH", price=Decimal("1.0000")
    )
    item = get_or_create_inventory(warehouse, product=product)
    with pytest.raises(ValidationError):
        transfer_stock(item, warehouse, 1)


def test_denormalized_variant_stock_synced(variant_item, user):
    receive_stock(variant_item, 15, actor=user)
    variant_item.refresh_from_db()
    variant = variant_item.variant
    variant.refresh_from_db()
    assert variant.stock_quantity == 15

    reserve_stock(variant_item, 5)
    consume_stock(variant_item, 5)
    variant_item.variant.refresh_from_db()
    assert variant_item.variant.stock_quantity == 10


def test_transaction_audit_trail_is_complete(variant_item, user):
    receive_stock(variant_item, 10, actor=user)
    reserve_stock(variant_item, 3)
    consume_stock(variant_item, 3)
    adjust_stock(variant_item, -1)

    txs = list(
        InventoryTransaction.objects.filter(inventory_item=variant_item).order_by("created_at")
    )
    assert [t.transaction_type for t in txs] == ["receive", "reserve", "ship", "adjust"]
    assert txs[-1].resulting_stock == 6
    assert txs[-1].resulting_reserved == 0


def test_inventory_permissions_declared(db):
    from apps.identity.models import Permission

    ensure_inventory_permissions()
    assert Permission.objects.filter(codename="inventory.adjust", source="core").exists()
    assert Permission.objects.filter(codename="inventory.warehouse.manage").exists()


def test_inventory_for_variant_helper(store, warehouse):
    product = create_product(store, "Helper Product", product_type="variant")
    variant = add_variant(product, "HLP-1", Decimal("1.0000"))
    assert inventory_for_variant(variant) is None
    get_or_create_inventory(warehouse, variant=variant)
    assert inventory_for_variant(variant) is not None
