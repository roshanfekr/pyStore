from decimal import Decimal

import pytest

from apps.catalog.services import add_variant, create_product, publish_product
from apps.pricing.engine import (
    CurrencyPriceUnavailable,
    explicit_currency_price,
    resolve_product_price,
)
from apps.pricing.models import PriceList, PriceListEntry, ProductPrice, ScheduledPrice
from apps.stores.services import create_store
from datetime import timedelta
from django.utils import timezone

pytestmark = [pytest.mark.django_db]

PRICE = Decimal("100.0000")


@pytest.fixture
def store(db):
    return create_store("Currency Pricing Store")


@pytest.fixture
def product(store):
    return create_product(store, "Currency Thing", price=PRICE)


def test_explicit_currency_price_is_used_without_conversion(store, product):
    ProductPrice.objects.create(product=product, currency="USD", price=Decimal("18.0000"))

    assert (
        resolve_product_price(product, store=store, currency="USD") == Decimal("18.0000")
    )
    # A second currency without an explicit price stays unpurchasable; the
    # USD price is never converted (FR-CUR-004).
    with pytest.raises(CurrencyPriceUnavailable):
        resolve_product_price(product, store=store, currency="EUR")


def test_missing_explicit_price_is_not_purchasable_in_that_currency(store, product):
    with pytest.raises(CurrencyPriceUnavailable):
        resolve_product_price(product, store=store, currency="USD")


def test_base_currency_keeps_the_stored_base_price(store, product):
    # No explicit rows exist: the base price remains effective (P2).
    assert resolve_product_price(product, store=store, currency="IRT") == PRICE
    assert resolve_product_price(product, store=store) == PRICE


def test_explicit_base_currency_price_replaces_the_base_price(store, product):
    ProductPrice.objects.create(product=product, currency="IRT", price=Decimal("120.0000"))

    assert resolve_product_price(product, store=store, currency="IRT") == Decimal("120.0000")


def test_currency_price_is_exact_to_the_product_or_variant(store):
    product = create_product(store, "Exact Thing", product_type="variant")
    variant = add_variant(product, "CUR-1", Decimal("77.0000"))
    ProductPrice.objects.create(product=product, currency="USD", price=Decimal("18.0000"))

    # A product-level price is never used as a variant's price (FR-CUR-002).
    with pytest.raises(CurrencyPriceUnavailable):
        resolve_product_price(product, variant, store=store, currency="USD")

    ProductPrice.objects.create(product=product, variant=variant, currency="USD", price=Decimal("19.0000"))
    assert (
        resolve_product_price(product, variant, store=store, currency="USD")
        == Decimal("19.0000")
    )
    assert explicit_currency_price(product, variant, "usd") == Decimal("19.0000")


def test_pricelist_still_wins_in_the_base_currency(store, product):
    ProductPrice.objects.create(product=product, currency="IRT", price=Decimal("120.0000"))
    price_list = PriceList.objects.create(name="VIP", priority=1)
    PriceListEntry.objects.create(price_list=price_list, product=product, price=Decimal("80.0000"))

    assert resolve_product_price(product, store=store, currency="IRT") == Decimal("80.0000")


def test_scheduled_price_still_applies_in_the_base_currency(store, product):
    ProductPrice.objects.create(product=product, currency="IRT", price=Decimal("120.0000"))
    now = timezone.now()
    ScheduledPrice.objects.create(
        product=product, price=Decimal("90.0000"), start_at=now - timedelta(hours=1)
    )

    assert resolve_product_price(product, store=store, currency="IRT") == Decimal("90.0000")


def test_product_without_any_price_still_raises_value_error(store):
    product = create_product(store, "No Price", product_type="variant")
    with pytest.raises(ValueError):
        resolve_product_price(product, store=store)


def test_unpriced_variant_product_is_not_purchasable_in_other_currencies(store):
    product = create_product(store, "Unpriced Variant", product_type="variant")
    variant = add_variant(product, "CUR-2", Decimal("77.0000"))
    publish_product(product)

    assert resolve_product_price(product, variant, store=store, currency="IRT") == Decimal("77.0000")
    with pytest.raises(CurrencyPriceUnavailable):
        resolve_product_price(product, variant, store=store, currency="USD")
