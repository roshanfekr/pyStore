from datetime import timedelta
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.catalog.services import add_variant, create_product
from apps.identity.services.roles import ensure_role, grant_role
from apps.pricing.engine import resolve_product_price
from apps.pricing.models import PriceList, PriceListEntry, ScheduledPrice
from apps.pricing.permissions import ensure_pricing_permissions
from apps.stores.services import create_store

User = get_user_model()

pytestmark = [pytest.mark.django_db]

PRICE = Decimal("100.0000")


@pytest.fixture
def store(db):
    return create_store("Pricing Store")


@pytest.fixture
def customer(db):
    return User.objects.create_user(email="priced@example.com", password="Str0ng!Passw0rd")


@pytest.fixture
def product(store):
    return create_product(store, "Priced Thing", price=PRICE)


def test_base_price_default(store, product):
    assert resolve_product_price(product) == PRICE


def test_variant_base_price(store):
    product = create_product(store, "Variant Priced", product_type="variant")
    variant = add_variant(product, "PRC-1", Decimal("77.0000"))
    assert resolve_product_price(product, variant) == Decimal("77.0000")


def test_customer_specific_price_wins(store, product, customer):
    price_list = PriceList.objects.create(name="VIP", customer=customer, priority=5)
    PriceListEntry.objects.create(price_list=price_list, product=product, price=Decimal("80.0000"))

    assert resolve_product_price(product, customer=customer) == Decimal("80.0000")
    assert resolve_product_price(product) == PRICE


def test_role_specific_price(store, product, customer):
    role = ensure_role("Wholesale")
    grant_role(customer, "Wholesale")

    price_list = PriceList.objects.create(name="Wholesale Prices", role=role, priority=1)
    PriceListEntry.objects.create(price_list=price_list, product=product, price=Decimal("60.0000"))

    assert resolve_product_price(product, customer=customer) == Decimal("60.0000")


def test_store_specific_price(store, product):
    other_store = create_store("Other Priced Store")
    price_list = PriceList.objects.create(name="Store Prices", store=store, priority=1)
    PriceListEntry.objects.create(price_list=price_list, product=product, price=Decimal("55.0000"))

    assert resolve_product_price(product, store=store) == Decimal("55.0000")
    assert resolve_product_price(product, store=other_store) == PRICE


def test_specificity_customer_beats_role(store, product, customer):
    role = ensure_role("Members")
    grant_role(customer, "Members")

    role_list = PriceList.objects.create(name="Role List", role=role, priority=99)
    PriceListEntry.objects.create(price_list=role_list, product=product, price=Decimal("70.0000"))

    customer_list = PriceList.objects.create(name="Customer List", customer=customer, priority=1)
    PriceListEntry.objects.create(price_list=customer_list, product=product, price=Decimal("50.0000"))

    assert resolve_product_price(product, customer=customer) == Decimal("50.0000")


def test_priority_breaks_ties(store, product, customer):
    list_low = PriceList.objects.create(name="Low", customer=customer, priority=1)
    PriceListEntry.objects.create(price_list=list_low, product=product, price=Decimal("40.0000"))

    list_high = PriceList.objects.create(name="High", customer=customer, priority=10)
    PriceListEntry.objects.create(price_list=list_high, product=product, price=Decimal("45.0000"))

    assert resolve_product_price(product, customer=customer) == Decimal("45.0000")


def test_quantity_pricing_tiers(store, product):
    price_list = PriceList.objects.create(name="Tiers", priority=1)
    PriceListEntry.objects.create(
        price_list=price_list, product=product, price=Decimal("95.0000"), min_quantity=1
    )
    PriceListEntry.objects.create(
        price_list=price_list, product=product, price=Decimal("85.0000"), min_quantity=5, max_quantity=9
    )
    PriceListEntry.objects.create(
        price_list=price_list, product=product, price=Decimal("70.0000"), min_quantity=10
    )

    assert resolve_product_price(product, quantity=1) == Decimal("95.0000")
    assert resolve_product_price(product, quantity=5) == Decimal("85.0000")
    assert resolve_product_price(product, quantity=9) == Decimal("85.0000")
    assert resolve_product_price(product, quantity=10) == Decimal("70.0000")


def test_quantity_out_of_range_falls_through(store, product):
    price_list = PriceList.objects.create(name="Narrow", priority=1)
    PriceListEntry.objects.create(
        price_list=price_list, product=product, price=Decimal("80.0000"), min_quantity=10
    )

    assert resolve_product_price(product, quantity=2) == PRICE


def test_scheduled_price_sale(store, product):
    now = timezone.now()
    ScheduledPrice.objects.create(
        product=product,
        price=Decimal("90.0000"),
        start_at=now - timedelta(hours=1),
        end_at=now + timedelta(days=1),
    )
    assert resolve_product_price(product) == Decimal("90.0000")


def test_scheduled_price_not_yet_or_expired_ignored(store, product):
    now = timezone.now()
    ScheduledPrice.objects.create(
        product=product, price=Decimal("90.0000"), start_at=now + timedelta(days=1)
    )
    assert resolve_product_price(product) == PRICE

    ScheduledPrice.objects.create(
        product=product, price=Decimal("80.0000"), start_at=now - timedelta(days=2),
        end_at=now - timedelta(days=1),
    )
    assert resolve_product_price(product) == PRICE


def test_pricelist_beats_scheduled_price(store, product, customer):
    now = timezone.now()
    ScheduledPrice.objects.create(
        product=product, price=Decimal("90.0000"), start_at=now - timedelta(hours=1)
    )
    price_list = PriceList.objects.create(name="Special", customer=customer, priority=1)
    PriceListEntry.objects.create(price_list=price_list, product=product, price=Decimal("60.0000"))

    assert resolve_product_price(product, customer=customer) == Decimal("60.0000")


def test_inactive_pricelist_ignored(store, product):
    price_list = PriceList.objects.create(name="Off", priority=1, is_active=False)
    PriceListEntry.objects.create(price_list=price_list, product=product, price=Decimal("10.0000"))
    assert resolve_product_price(product) == PRICE


def test_variant_entry_over_product_entry(store, product):
    variant_product = create_product(store, "Mixed Variant", product_type="variant")
    variant = add_variant(variant_product, "PRC-V", Decimal("77.0000"))
    price_list = PriceList.objects.create(name="Mixed", priority=1)
    PriceListEntry.objects.create(price_list=price_list, product=variant_product, price=Decimal("50.0000"))
    PriceListEntry.objects.create(price_list=price_list, variant=variant, price=Decimal("65.0000"))

    assert resolve_product_price(variant_product, variant) == Decimal("65.0000")


def test_pricing_permissions_declared(db):
    from apps.identity.models import Permission

    ensure_pricing_permissions()
    assert Permission.objects.filter(codename="pricing.manage").exists()
