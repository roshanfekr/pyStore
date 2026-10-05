from decimal import Decimal

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.catalog.models import (
    Brand,
    Category,
    ProductAttribute,
    ProductSEO,
)
from apps.catalog.services import (
    add_bundle_item,
    add_related_product,
    add_specification,
    add_variant,
    attach_download,
    create_product,
    ensure_catalog_permissions,
    publish_product,
    resolve_price,
    set_variant_attributes,
    unpublish_product,
    update_product,
    update_seo,
)
from apps.stores.services import create_store
from apps.vendors.services import create_vendor
from core.exceptions import ConflictError, ValidationError

pytestmark = [pytest.mark.django_db]

PRICE = Decimal("150.0000")


@pytest.fixture
def store(db):
    return create_store("Catalog Store")


@pytest.fixture
def store_b(db):
    return create_store("Other Store")


@pytest.fixture
def simple_product(store):
    return create_product(
        store, "Coffee Maker", price=PRICE, description="Brews coffee", sku="CM-001"
    )


def _product_in(store, name, **kwargs):
    return create_product(store, name, **kwargs)


def test_create_product_with_seo_and_event(store, simple_product):
    assert simple_product.slug == "coffee-maker"
    assert ProductSEO.objects.filter(product=simple_product).exists()
    assert simple_product.product_type == "simple"
    assert simple_product.price == PRICE


def test_product_slug_unique():
    store = create_store("Slug Store")
    first = create_product(store, "Widget", price=PRICE)
    second = create_product(store, "Widget", price=PRICE)
    assert first.slug == "widget"
    assert second.slug == "widget-2"


def test_create_product_requires_name(store):
    with pytest.raises(ValidationError):
        create_product(store, "  ")


def test_create_product_requires_price_for_simple(store):
    with pytest.raises(ValidationError):
        create_product(store, "No Price", product_type="simple")


def test_update_product_allowed_fields(simple_product):
    updated = update_product(simple_product, description="New desc", price=Decimal("199.0000"))
    assert updated.price == Decimal("199.0000")
    with pytest.raises(ValidationError):
        update_product(simple_product, hacker_field="x")


def test_publish_and_unpublish(simple_product):
    published = publish_product(simple_product)
    assert published.is_published is True
    assert published.published_at is not None

    unpublished = unpublish_product(simple_product)
    assert unpublished.is_published is False


def test_publish_requires_price(simple_product):
    simple_product.price = None
    simple_product.save()
    with pytest.raises(ValidationError):
        publish_product(simple_product)


def test_category_hierarchy():
    root = Category.objects.create(name="Electronics", slug="electronics")
    child = Category.objects.create(name="Laptops", slug="laptops", parent=root)
    grandchild = Category.objects.create(name="Gaming", slug="gaming-laptops", parent=child)

    assert grandchild.ancestors() == [root, child]
    assert root.descendant_ids() == [child.id, grandchild.id]
    assert root.children.count() == 1


def test_brand_and_tags():
    brand = Brand.objects.create(name="Acme", slug="acme")
    store = create_store("Brand Store")
    product = create_product(store, "Tagged Product", price=PRICE, brand=brand)

    from apps.catalog.models import Tag

    tag = Tag.objects.create(name="Sale", slug="sale")
    product.tags.add(tag)
    assert product.brand == brand
    assert list(product.tags.all()) == [tag]


def test_variants_flow(store):
    product = create_product(store, "T-Shirt", product_type="variant")

    variant_a = add_variant(product, "TSH-M-RED", Decimal("20.0000"))
    add_variant(product, "TSH-L-BLU", Decimal("22.0000"))

    assert product.variants.count() == 2

    ProductAttribute.objects.create(name="Color", slug="color")
    set_variant_attributes(variant_a, {"color": "Red"})

    assert variant_a.attributes.first().value.value == "Red"

    with pytest.raises(ConflictError):
        add_variant(product, "TSH-M-RED", Decimal("20.0000"))

    simple = create_product(store, "Simple Thing", price=PRICE)
    with pytest.raises(ValidationError):
        add_variant(simple, "SMP-1", PRICE)


def test_variant_carries_full_data(store):
    product = create_product(store, "Sneaker", product_type="variant")
    variant = add_variant(
        product,
        "SNK-42",
        Decimal("89.0000"),
        compare_at_price=Decimal("120.0000"),
        stock_quantity=7,
        weight=Decimal("1.2000"),
        length=Decimal("30.0000"),
        width=Decimal("12.0000"),
        height=Decimal("10.0000"),
    )
    assert variant.stock_quantity == 7
    assert variant.weight == Decimal("1.2000")
    assert variant.compare_at_price == Decimal("120.0000")


def test_variant_product_requires_variant_to_publish(store):
    product = create_product(store, "Variant Empty", product_type="variant")
    with pytest.raises(ValidationError):
        publish_product(product)


def test_specifications(store, simple_product):
    spec = add_specification(simple_product, "Power", "1000W")
    add_specification(simple_product, "Color", "Black")
    assert simple_product.specifications.count() == 2
    assert spec.position == 0


def test_product_relations(store, simple_product):
    other = _product_in(store, "Other Product", price=PRICE)

    add_related_product(simple_product, other, "related")
    add_related_product(simple_product, other, "cross_sell")
    assert simple_product.relations.filter(relation_type="cross_sell").exists()

    with pytest.raises(ConflictError):
        add_related_product(simple_product, other, "related")

    with pytest.raises(ValidationError):
        add_related_product(simple_product, simple_product, "upsell")

    with pytest.raises(ValidationError):
        add_related_product(simple_product, other, "bogus_type")


def test_bundle_items(store, simple_product):
    bundle = create_product(store, "Starter Kit", product_type="bundled")
    child = create_product(store, "Kit Part", price=Decimal("10.0000"))

    add_bundle_item(bundle, child, quantity=2)
    assert bundle.bundle_items.count() == 1

    with pytest.raises(ConflictError):
        add_bundle_item(bundle, child)

    with pytest.raises(ValidationError):
        add_bundle_item(bundle, bundle)

    with pytest.raises(ValidationError):
        add_bundle_item(simple_product, child)


def test_downloadable_product(store):
    from apps.identity.models import User
    from apps.vendors.services import create_vendor

    owner = User.objects.create_user(email="dl@example.com", password="Str0ng!Passw0rd")
    vendor = create_vendor(owner=owner, name="DL Vendor", store=store)
    digital = create_product(
        store, "E-Book", product_type="downloadable", price=PRICE, vendor=vendor
    )
    file = SimpleUploadedFile("manual.pdf", b"PDF CONTENT", content_type="application/pdf")

    download = attach_download(digital, file, label="User manual")

    assert download.label == "User manual"
    assert download.max_downloads == 5

    physical = _product_in(store, "Physical Thing", price=PRICE)
    with pytest.raises(ValidationError):
        attach_download(physical, file, label="Nope")


def test_seo_update(simple_product):
    seo = update_seo(
        simple_product,
        meta_title="Best Coffee Maker",
        meta_description="Brew the perfect cup",
        noindex=False,
    )
    assert seo.meta_title == "Best Coffee Maker"
    with pytest.raises(ValidationError):
        update_seo(simple_product, junk="x")


def test_pricing_default_and_override(store, simple_product):
    assert resolve_price(simple_product) == PRICE

    product = create_product(store, "Shirt", product_type="variant")
    variant = add_variant(product, "SHT-M", Decimal("30.0000"))
    assert resolve_price(product, variant) == Decimal("30.0000")

    from apps.catalog.pricing import PricingRegistry

    registry = PricingRegistry()

    def ten_percent_off(product, variant, context):
        base = variant.price if variant else product.price
        return base * Decimal("0.9")

    registry.register(ten_percent_off)
    assert registry.resolve(product, variant) == Decimal("27.0000")
    registry.reset()


def test_products_are_scoped_by_store(store, store_b, simple_product):
    assert store.products.filter(slug="coffee-maker").exists()
    assert store_b.products.filter(slug="coffee-maker").exists() is False


def test_vendor_products_relationship(store, owner_factory=None):
    from apps.identity.models import User

    owner = User.objects.create_user(email="vshop@example.com", password="Str0ng!Passw0rd")
    vendor = create_vendor(owner=owner, name="Vendor Shop", store=store)
    product = create_product(store, "Vendor Product", price=PRICE, vendor=vendor)

    assert vendor.products.filter(pk=product.pk).exists()


def test_catalog_permissions_declared(db):
    from apps.identity.models import Permission

    ensure_catalog_permissions()
    for code in ["catalog.product.view", "catalog.product.create", "catalog.product.delete"]:
        assert Permission.objects.filter(codename=code, source="core").exists()
