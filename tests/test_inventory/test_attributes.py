import pytest

from apps.catalog.models import ProductAttribute, ProductAttributeValue
from apps.catalog.services import (
    get_product_attributes,
    set_product_attribute,
)
from core.exceptions import ValidationError

pytestmark = [pytest.mark.django_db]


@pytest.fixture
def store(db):
    from apps.stores.services import create_store

    return create_store("Attr Store")


@pytest.fixture
def product(store):
    from decimal import Decimal

    from apps.catalog.services import create_product

    return create_product(store, "Attr Product", price=Decimal("50.0000"))


def _attr(slug, vtype, with_values=None):
    attribute, _ = ProductAttribute.objects.get_or_create(
        name=slug.title(), slug=slug, defaults={"value_type": vtype}
    )
    if attribute.value_type != vtype:
        attribute.value_type = vtype
        attribute.save()
    for value in with_values or []:
        ProductAttributeValue.objects.get_or_create(attribute=attribute, value=value)
    return attribute


def test_text_attribute(product):
    set_product_attribute(product, "material", "Cotton")
    assert get_product_attributes(product)["material"] == "Cotton"


def test_number_attribute(product):
    _attr("screen-size", "number")
    set_product_attribute(product, "screen-size", 6.7)
    assert get_product_attributes(product)["screen-size"] == 6.7

    with pytest.raises(ValidationError):
        set_product_attribute(product, "screen-size", "big")


def test_boolean_attribute(product):
    _attr("waterproof", "boolean")
    set_product_attribute(product, "waterproof", True)
    assert get_product_attributes(product)["waterproof"] is True

    with pytest.raises(ValidationError):
        set_product_attribute(product, "waterproof", "yes")


def test_color_attribute_valid_and_invalid(product):
    _attr("body-color", "color")
    set_product_attribute(product, "body-color", "#FF8800")
    assert get_product_attributes(product)["body-color"] == "#FF8800"

    with pytest.raises(ValidationError):
        set_product_attribute(product, "body-color", "orange")


def test_select_attribute_requires_predefined_value(product):
    _attr("warranty", "select", with_values=["12 months", "24 months"])
    set_product_attribute(product, "warranty", "24 months")
    assert get_product_attributes(product)["warranty"] == "24 months"

    with pytest.raises(ValidationError):
        set_product_attribute(product, "warranty", "36 months")


def test_multi_select_attribute(product):
    _attr("connectivity", "multi_select", with_values=["Bluetooth", "WiFi", "NFC"])
    set_product_attribute(product, "connectivity", ["Bluetooth", "NFC"])
    assert get_product_attributes(product)["connectivity"] == ["Bluetooth", "NFC"]

    with pytest.raises(ValidationError):
        set_product_attribute(product, "connectivity", ["Bluetooth", "5G"])

    with pytest.raises(ValidationError):
        set_product_attribute(product, "connectivity", "Bluetooth")


def test_size_attribute(product):
    _attr("shoe-size", "size")
    set_product_attribute(product, "shoe-size", "42")
    assert get_product_attributes(product)["shoe-size"] == "42"


def test_setting_again_updates_not_duplicates(product):
    _attr("fabric", "text")
    set_product_attribute(product, "fabric", "Cotton")
    set_product_attribute(product, "fabric", "Wool")
    assert get_product_attributes(product) == {"fabric": "Wool"}
    assert product.attribute_assignments.count() == 1


def test_unknown_type_rejected(product, db):
    ProductAttribute.objects.create(name="Weird", slug="weird", value_type="bogus")
    with pytest.raises(ValidationError):
        set_product_attribute(product, "weird", "anything")
