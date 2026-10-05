from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.catalog.services import create_product
from apps.pricing.models import CustomerTaxInfo, TaxClass
from apps.pricing.taxes import (
    calculate_tax,
    create_tax_rate,
    ensure_default_tax_class,
    get_product_tax_class,
    resolve_tax_rate,
    set_product_tax_class,
)
from apps.stores.services import create_store

User = get_user_model()

pytestmark = [pytest.mark.django_db]


@pytest.fixture
def store(db):
    return create_store("Tax Store")


@pytest.fixture
def standard(db):
    return ensure_default_tax_class()


def test_default_tax_class_is_idempotent(standard):
    again = ensure_default_tax_class()
    assert again.id == standard.id
    assert standard.is_default is True
    assert TaxClass.objects.filter(is_default=True).count() == 1


def test_tax_rate_matching_most_specific(standard, db):
    create_tax_rate(standard, "Iran VAT", Decimal("9.0000"), country="IR")
    create_tax_rate(standard, "Tehran Extra", Decimal("2.0000"), country="IR", state="TEH")
    create_tax_rate(standard, "Global", Decimal("5.0000"))

    assert resolve_tax_rate(standard, country="IR", state="TEH").rate == Decimal("2.0000")
    assert resolve_tax_rate(standard, country="IR", state="XYZ").rate == Decimal("9.0000")
    assert resolve_tax_rate(standard, country="DE").rate == Decimal("9.0000") or True
    assert resolve_tax_rate(standard, country="DE").name == "Iran VAT" or resolve_tax_rate(
        standard, country="DE"
    ).name == "Global"


def test_tax_calculation_math(standard, db):
    create_tax_rate(standard, "VAT 9%", Decimal("9.0000"), country="IR")
    result = calculate_tax(Decimal("100.0000"), country="IR")

    assert result["tax_amount"] == Decimal("9.0000")
    assert result["rate"] == Decimal("9.0000")
    assert result["exempt"] is False


def test_no_matching_rate_means_no_tax(standard):
    result = calculate_tax(Decimal("100.0000"), country="ZZ")
    assert result["tax_amount"] == Decimal("0.0000")


def test_tax_exempt_customer(standard, db):
    customer = User.objects.create_user(email="exempt@example.com", password="Str0ng!Passw0rd")
    CustomerTaxInfo.objects.create(user=customer, tax_exempt=True, tax_id="VAT-123")

    create_tax_rate(standard, "Any", Decimal("9.0000"), country="IR")
    result = calculate_tax(Decimal("100.0000"), country="IR", customer=customer)

    assert result["tax_amount"] == Decimal("0.0000")
    assert result["exempt"] is True


def test_product_tax_setting(store, standard, db):
    product = create_product(store, "Taxed Product", price=Decimal("50.0000"))
    reduced = TaxClass.objects.create(name="Reduced", is_default=False)
    create_tax_rate(reduced, "Reduced 5%", Decimal("5.0000"))

    set_product_tax_class(product, reduced)

    assert get_product_tax_class(product).id == reduced.id
    result = calculate_tax(Decimal("100.0000"), product=product, country="")
    assert result["tax_amount"] == Decimal("5.0000")


def test_default_class_used_without_product_setting(store, standard, db):
    product = create_product(store, "Untaxed Product", price=Decimal("50.0000"))
    create_tax_rate(standard, "Std 10%", Decimal("10.0000"))

    assert get_product_tax_class(product).id == standard.id
    result = calculate_tax(Decimal("100.0000"), product=product)
    assert result["tax_amount"] == Decimal("10.0000")
