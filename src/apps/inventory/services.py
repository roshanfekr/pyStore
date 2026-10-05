from django.db.models import F

from apps.identity.services.roles import ensure_permission
from apps.inventory.events import InventoryChanged, InventoryLowStock
from apps.inventory.models import (
    InventoryItem,
    InventoryTransaction,
    Warehouse,
    WarehouseLocation,
)
from core.exceptions import ConflictError, ValidationError
from core.infrastructure import atomic

INVENTORY_PERMISSIONS = [
    ("inventory.view", "View inventory"),
    ("inventory.adjust", "Adjust inventory"),
    ("inventory.transfer", "Transfer inventory"),
    ("inventory.warehouse.manage", "Manage warehouses"),
]


def ensure_inventory_permissions() -> None:
    for codename, display_name in INVENTORY_PERMISSIONS:
        ensure_permission(codename, display_name=display_name, source="core")


def create_warehouse(
    store, name: str, code: str, *, address_line: str = "", city: str = "", state: str = "",
    postal_code: str = "", country: str = "", is_default: bool = False,
) -> Warehouse:
    if Warehouse.objects.filter(code=code).exists():
        raise ConflictError(f"Warehouse code {code!r} already exists", code="inventory.warehouse_taken")
    return Warehouse.objects.create(
        store=store,
        name=name,
        code=code,
        address_line=address_line,
        city=city,
        state=state,
        postal_code=postal_code,
        country=country,
        is_default=is_default,
    )


def add_warehouse_location(warehouse: Warehouse, code: str, description: str = "") -> WarehouseLocation:
    if WarehouseLocation.objects.filter(warehouse=warehouse, code=code).exists():
        raise ConflictError("Location already exists", code="inventory.location_taken")
    return WarehouseLocation.objects.create(warehouse=warehouse, code=code, description=description)


def get_or_create_inventory(warehouse: Warehouse, *, product=None, variant=None, **kwargs) -> InventoryItem:
    if (product is None) == (variant is None):
        raise ValidationError(
            "Exactly one of product or variant must be provided",
            code="inventory.target_required",
        )
    lookup = {"warehouse": warehouse, "product": product} if product else {
        "warehouse": warehouse, "variant": variant
    }
    item, created = InventoryItem.objects.get_or_create(**lookup, defaults=kwargs)
    return item


def inventory_for_variant(variant, warehouse: Warehouse | None = None) -> InventoryItem | None:
    queryset = InventoryItem.objects.filter(variant=variant)
    if warehouse is not None:
        queryset = queryset.filter(warehouse=warehouse)
    return queryset.first()


def _sync_denormalized(item: InventoryItem) -> None:
    if item.variant_id:
        variant = item.variant
        variant.stock_quantity = item.available_quantity
        variant.save(update_fields=["stock_quantity"])
    elif item.product_id:
        product = item.product
        product.stock_quantity = item.available_quantity
        product.save(update_fields=["stock_quantity"])


@atomic()
def _mutate(
    item: InventoryItem,
    *,
    transaction_type: str,
    stock_delta: int = 0,
    reserved_delta: int = 0,
    actor=None,
    reference: str = "",
    note: str = "",
    allow_oversell: bool = False,
) -> InventoryItem:
    if stock_delta == 0 and reserved_delta == 0:
        raise ValidationError("No-op inventory mutation", code="inventory.noop")

    locked = InventoryItem.objects.select_for_update().get(pk=item.pk)
    new_stock = locked.stock_quantity + stock_delta
    new_reserved = locked.reserved_quantity + reserved_delta

    if new_stock < 0:
        raise ConflictError(
            "Insufficient stock on hand", code="inventory.insufficient_stock"
        )
    if new_reserved < 0:
        raise ConflictError("Nothing to release", code="inventory.nothing_reserved")
    if reserved_delta > 0:
        available = locked.stock_quantity - locked.reserved_quantity
        if reserved_delta > available and not (allow_oversell and locked.backorder_allowed):
            raise ConflictError(
                f"Insufficient available stock ({available})", code="inventory.insufficient_available"
            )
    if stock_delta < 0 and transaction_type != "adjust":
        pass

    InventoryItem.objects.filter(pk=locked.pk).update(
        stock_quantity=F("stock_quantity") + stock_delta,
        reserved_quantity=F("reserved_quantity") + reserved_delta,
    )
    locked.refresh_from_db()

    InventoryTransaction.objects.create(
        inventory_item=locked,
        transaction_type=transaction_type,
        stock_delta=stock_delta,
        reserved_delta=reserved_delta,
        resulting_stock=locked.stock_quantity,
        resulting_reserved=locked.reserved_quantity,
        reference=reference,
        note=note,
        actor=actor,
    )
    return locked


def _post_mutate_events(item: InventoryItem, transaction_type: str) -> None:
    from core.events import dispatcher

    dispatcher.dispatch(
        InventoryChanged(
            inventory_id=str(item.id),
            transaction_type=transaction_type,
            stock_quantity=item.stock_quantity,
            reserved_quantity=item.reserved_quantity,
        )
    )
    if item.stock_status == "low_stock" or item.stock_status == "out_of_stock":
        dispatcher.dispatch(
            InventoryLowStock(
                inventory_id=str(item.id),
                available_quantity=item.available_quantity,
                product_id=str(item.product_id or (item.variant.product_id if item.variant_id else "")),
            )
        )


def _check_quantity(quantity: int) -> None:
    if quantity <= 0:
        raise ValidationError("Quantity must be positive", code="inventory.bad_quantity")


def receive_stock(
    item: InventoryItem, quantity: int, *, actor=None, reference: str = "", note: str = ""
) -> InventoryItem:
    _check_quantity(quantity)
    item = _mutate(
        item, transaction_type=InventoryTransaction.TYPE_RECEIVE, stock_delta=quantity,
        actor=actor, reference=reference, note=note,
    )
    _sync_denormalized(item)
    _post_mutate_events(item, InventoryTransaction.TYPE_RECEIVE)
    return item


def adjust_stock(
    item: InventoryItem, delta: int, *, actor=None, reference: str = "", note: str = ""
) -> InventoryItem:
    item = _mutate(
        item, transaction_type=InventoryTransaction.TYPE_ADJUST, stock_delta=delta,
        actor=actor, reference=reference, note=note or "manual adjustment",
    )
    _sync_denormalized(item)
    _post_mutate_events(item, InventoryTransaction.TYPE_ADJUST)
    return item


def reserve_stock(
    item: InventoryItem, quantity: int, *, actor=None, reference: str = "", note: str = ""
) -> InventoryItem:
    _check_quantity(quantity)
    item = _mutate(
        item, transaction_type=InventoryTransaction.TYPE_RESERVE, reserved_delta=quantity,
        actor=actor, reference=reference, note=note,
        allow_oversell=True,
    )
    _post_mutate_events(item, InventoryTransaction.TYPE_RESERVE)
    return item


def release_stock(
    item: InventoryItem, quantity: int, *, actor=None, reference: str = "", note: str = ""
) -> InventoryItem:
    _check_quantity(quantity)
    item = _mutate(
        item, transaction_type=InventoryTransaction.TYPE_RELEASE, reserved_delta=-quantity,
        actor=actor, reference=reference, note=note,
    )
    _post_mutate_events(item, InventoryTransaction.TYPE_RELEASE)
    return item


def consume_stock(
    item: InventoryItem, quantity: int, *, actor=None, reference: str = "", note: str = ""
) -> InventoryItem:
    _check_quantity(quantity)
    item = _mutate(
        item, transaction_type=InventoryTransaction.TYPE_SHIP, stock_delta=-quantity,
        reserved_delta=-quantity, actor=actor, reference=reference, note=note,
    )
    _sync_denormalized(item)
    _post_mutate_events(item, InventoryTransaction.TYPE_SHIP)
    return item


def transfer_stock(
    item: InventoryItem, target_warehouse: Warehouse, quantity: int, *, actor=None, reference: str = "", note: str = ""
) -> tuple[InventoryTransaction, InventoryTransaction]:
    if quantity <= 0:
        raise ValidationError("Quantity must be positive", code="inventory.bad_quantity")
    if target_warehouse.id == item.warehouse_id:
        raise ValidationError("Cannot transfer to the same warehouse", code="inventory.same_warehouse")

    source_item = _mutate(
        item, transaction_type=InventoryTransaction.TYPE_TRANSFER_OUT, stock_delta=-quantity,
        actor=actor, reference=reference, note=note or f"transfer to {target_warehouse.code}",
    )
    target_item = get_or_create_inventory(target_warehouse, product=source_item.product, variant=source_item.variant)
    target_item = _mutate(
        target_item, transaction_type=InventoryTransaction.TYPE_TRANSFER_IN, stock_delta=quantity,
        actor=actor, reference=reference, note=note or f"transfer from {source_item.warehouse.code}",
    )
    _sync_denormalized(source_item)
    return source_item, target_item
