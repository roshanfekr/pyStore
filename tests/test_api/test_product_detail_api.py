from decimal import Decimal

import pytest

from apps.catalog.models import ProductAttribute, ProductImage
from apps.catalog.services import (
    add_variant,
    create_product,
    publish_product,
    set_product_attribute,
    set_variant_attributes,
)
from apps.pricing.models import ProductPrice
from apps.stores.services import create_store, upsert_currency

pytestmark = [pytest.mark.django_db]


@pytest.fixture
def store(db):
    return create_store("Product Detail API Store")


@pytest.fixture
def published_product(store):
    product = create_product(
        store,
        "Detail Product",
        price=Decimal("100.0000"),
        stock_quantity=10,
        sku="DETAIL-1",
        description="A detailed product.",
    )
    publish_product(product)
    return product


@pytest.fixture
def variant_product(store):
    product = create_product(
        store, "Shirt", product_type="variant", price=None, description="A shirt."
    )
    color = ProductAttribute.objects.create(
        name="Color", slug="color", value_type="color", is_variant_option=True
    )
    size = ProductAttribute.objects.create(
        name="Size", slug="size", value_type="size", is_variant_option=True
    )
    set_product_attribute(product, "color", "#1e3a8a")
    set_product_attribute(product, "size", "M")
    red = add_variant(product, "SHIRT-RED-M", Decimal("120.0000"), stock_quantity=4)
    set_variant_attributes(red, {"color": "#ff0000", "size": "M"})
    blue = add_variant(product, "SHIRT-BLUE-M", Decimal("90.0000"), stock_quantity=0)
    set_variant_attributes(blue, {"color": "#0000ff", "size": "M"})
    publish_product(product)
    assert color.slug == "color"
    assert size.slug == "size"
    return product


def test_product_detail_returns_the_product_information(api_client, published_product):
    response = api_client.get(f"/api/v1/storefront/products/{published_product.slug}")
    assert response.status_code == 200
    assert response.data["name"] == "Detail Product"
    assert response.data["description"] == "A detailed product."
    assert response.data["sku"] == "DETAIL-1"
    assert response.data["product_type"] == "simple"
    # The price is displayed with the active currency (IRT has 0 decimals).
    assert response.data["price"] == "100 تومان"
    assert response.data["price_value"] == "100.0000"
    assert response.data["currency"]["code"] == "IRT"
    assert response.data["in_stock"] is True
    assert response.data["available_quantity"] == 10
    assert response.data["images"] == []
    assert response.data["variants"] == []
    assert response.data["options"] == []


def test_product_detail_exposes_the_product_images(api_client, published_product):
    ProductImage.objects.create(
        product=published_product, image="catalog/products/shirt.png", position=0
    )
    ProductImage.objects.create(
        product=published_product,
        image="catalog/products/shirt-2.png",
        alt_text="Shirt side view",
        position=1,
    )

    response = api_client.get(f"/api/v1/storefront/products/{published_product.slug}")
    assert response.status_code == 200
    assert len(response.data["images"]) == 2
    assert response.data["images"][0]["url"].endswith("catalog/products/shirt.png")
    assert response.data["images"][0]["alt"] == ""
    assert response.data["images"][1]["alt"] == "Shirt side view"


def test_product_detail_exposes_the_variant_combinations(api_client, variant_product):
    response = api_client.get(f"/api/v1/storefront/products/{variant_product.slug}")
    assert response.status_code == 200

    skus = [variant["sku"] for variant in response.data["variants"]]
    assert skus == ["SHIRT-BLUE-M", "SHIRT-RED-M"]

    by_sku = {variant["sku"]: variant for variant in response.data["variants"]}
    assert by_sku["SHIRT-RED-M"]["price"] == "120 تومان"
    assert by_sku["SHIRT-RED-M"]["price_value"] == "120.0000"
    assert by_sku["SHIRT-RED-M"]["in_stock"] is True
    assert by_sku["SHIRT-RED-M"]["available_quantity"] == 4
    assert by_sku["SHIRT-RED-M"]["attributes"] == {"color": "#ff0000", "size": "M"}
    assert by_sku["SHIRT-BLUE-M"]["in_stock"] is False
    assert by_sku["SHIRT-BLUE-M"]["available_quantity"] == 0

    options = {option["slug"]: option for option in response.data["options"]}
    assert options["color"]["name"] == "Color"
    assert options["color"]["type"] == "color"
    values = {value["value"]: value for value in options["color"]["values"]}
    # The values the variants carry are selectable, the product-level value
    # that no variant carries is not.
    assert values["#ff0000"]["swatch"] == "#ff0000"
    assert values["#ff0000"]["available"] is True
    assert values["#0000ff"]["available"] is False
    assert values["#1e3a8a"]["available"] is False
    assert options["size"]["values"][0]["value"] == "M"


def test_product_detail_reports_the_first_variant_as_the_selected_one(api_client, variant_product):
    response = api_client.get(f"/api/v1/storefront/products/{variant_product.slug}")
    assert response.status_code == 200
    # The variants are ordered by SKU, and the first one is preselected.
    assert response.data["selected_variant"] == "SHIRT-BLUE-M"
    assert response.data["price"] == "90 تومان"
    assert response.data["in_stock"] is True


def test_product_detail_hides_inactive_variants(api_client, variant_product):
    variant = variant_product.variants.get(sku="SHIRT-RED-M")
    variant.is_active = False
    variant.save()

    response = api_client.get(f"/api/v1/storefront/products/{variant_product.slug}")
    assert response.status_code == 200
    assert [variant["sku"] for variant in response.data["variants"]] == ["SHIRT-BLUE-M"]


def test_product_detail_is_not_found_for_an_unpublished_product(api_client, store):
    product = create_product(store, "Hidden", price=Decimal("5.0000"))

    response = api_client.get(f"/api/v1/storefront/products/{product.slug}")
    assert response.status_code == 404


def test_product_detail_is_not_found_for_an_unknown_product(api_client, db):
    assert api_client.get("/api/v1/storefront/products/does-not-exist").status_code == 404


def test_product_detail_uses_the_product_seo_metadata(api_client, published_product):
    response = api_client.get(f"/api/v1/storefront/products/{published_product.slug}")
    assert response.status_code == 200
    assert response.data["meta_title"] == "Detail Product"
    assert response.data["meta_description"] == "A detailed product."

    seo = published_product.seo
    seo.meta_title = "Detail Product | pyStore"
    seo.meta_description = "Buy the detail product."
    seo.save()

    response = api_client.get(f"/api/v1/storefront/products/{published_product.slug}")
    assert response.data["meta_title"] == "Detail Product | pyStore"
    assert response.data["meta_description"] == "Buy the detail product."


def test_cart_rejects_an_inactive_variant(api_client, store, variant_product):
    from rest_framework.test import APIClient

    client = APIClient(headers={"X-Cart-Session": "guest-session-1", "X-Store": store.slug})
    variant = variant_product.variants.get(sku="SHIRT-RED-M")
    variant.is_active = False
    variant.save()

    response = client.post(
        "/api/v1/cart/items",
        {"product": variant_product.slug, "quantity": 1, "variant": variant.sku},
        format="json",
    )
    assert response.status_code == 400
    assert response.data["error"]["code"] == "cart.variant_inactive"


def test_cart_accepts_an_active_variant(api_client, store, variant_product):
    from rest_framework.test import APIClient

    client = APIClient(headers={"X-Cart-Session": "guest-session-1", "X-Store": store.slug})
    response = client.post(
        "/api/v1/cart/items",
        {"product": variant_product.slug, "quantity": 2, "variant": "SHIRT-RED-M"},
        format="json",
    )
    assert response.status_code == 201
    assert response.data["subtotal"] == "240.0000"


def test_product_detail_shows_the_explicit_currency_price(api_client, store, published_product):
    upsert_currency("US Dollar", "USD", symbol="$", decimal_places=2)
    ProductPrice.objects.create(product=published_product, currency="USD", price=Decimal("18.0000"))

    client = api_client
    client.cookies["pystore_currency"] = "USD"
    response = client.get(f"/api/v1/storefront/products/{published_product.slug}")

    assert response.status_code == 200
    assert response.data["currency"]["code"] == "USD"
    assert response.data["price"] == "18.00 $"
    assert response.data["price_value"] == "18.0000"


def test_product_detail_reports_no_price_when_the_currency_has_none(api_client, store, published_product):
    upsert_currency("US Dollar", "USD", symbol="$", decimal_places=2)

    client = api_client
    client.cookies["pystore_currency"] = "USD"
    response = client.get(f"/api/v1/storefront/products/{published_product.slug}")

    assert response.status_code == 200
    # No conversion is invented for a currency without an explicit price
    # (FR-CUR-004): the price is reported as unavailable.
    assert response.data["price"] == ""
    assert response.data["price_value"] == ""


def test_product_detail_shows_the_variant_image(api_client, store, variant_product):
    variant = variant_product.variants.get(sku="SHIRT-RED-M")
    variant.image = "catalog/variants/2026/10/red.png"
    variant.save()

    response = api_client.get(f"/api/v1/storefront/products/{variant_product.slug}")
    assert response.status_code == 200
    by_sku = {variant["sku"]: variant for variant in response.data["variants"]}
    assert by_sku["SHIRT-RED-M"]["image"].endswith("catalog/variants/2026/10/red.png")
    assert by_sku["SHIRT-BLUE-M"]["image"] == ""
