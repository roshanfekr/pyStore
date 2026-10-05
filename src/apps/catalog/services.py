
import re

from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from apps.catalog.events import ProductCreated, ProductPublished
from apps.catalog.models import (
    RELATION_TYPES,
    Product,
    ProductAttribute,
    ProductAttributeAssignment,
    ProductAttributeValue,
    ProductBundleItem,
    ProductDownload,
    ProductRelation,
    ProductSEO,
    ProductSpecification,
    ProductVariant,
)
from apps.catalog.pricing import pricing_registry
from apps.identity.services.roles import ensure_permission
from core.exceptions import ConflictError, ValidationError

CATALOG_PERMISSIONS = [
    ("catalog.product.view", "View products"),
    ("catalog.product.create", "Create products"),
    ("catalog.product.update", "Update products"),
    ("catalog.product.delete", "Delete products"),
    ("catalog.category.manage", "Manage categories"),
    ("catalog.brand.manage", "Manage brands"),
]

HEX_COLOR_RE = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")


def ensure_catalog_permissions() -> None:
    for codename, display_name in CATALOG_PERMISSIONS:
        ensure_permission(codename, display_name=display_name, source="core")


def _unique_product_slug(name: str) -> str:
    base = slugify(name) or "product"
    slug = base
    counter = 2
    while Product.objects.filter(slug=slug).exists():
        slug = f"{base}-{counter}"
        counter += 1
    return slug


def _validate_product(product: Product) -> None:
    if product.product_type == "variant" and not product.variants.exists():
        raise ValidationError(
            "A variant product requires at least one variant", code="catalog.variant_required"
        )
    if product.product_type == "bundled" and not product.bundle_items.exists():
        raise ValidationError(
            "A bundled product requires at least one bundle item", code="catalog.bundle_required"
        )
    if product.price is None and product.product_type not in ("variant", "bundled"):
        raise ValidationError("Product price is required", code="catalog.price_required")


@transaction.atomic
def create_product(
    store,
    name: str,
    *,
    category=None,
    brand=None,
    vendor=None,
    product_type: str = "simple",
    price=None,
    compare_at_price=None,
    description: str = "",
    sku: str = "",
    stock_quantity: int = 0,
    recurring_billing_period: str | None = None,
) -> Product:
    if not name or not name.strip():
        raise ValidationError("Product name is required", code="catalog.name_required")
    if price is None and product_type not in ("variant", "bundled"):
        raise ValidationError("Product price is required", code="catalog.price_required")

    product = Product.objects.create(
        store=store,
        name=name.strip(),
        slug=_unique_product_slug(name),
        category=category,
        brand=brand,
        vendor=vendor,
        product_type=product_type,
        price=price,
        compare_at_price=compare_at_price,
        description=description,
        sku=sku,
        stock_quantity=stock_quantity,
        recurring_billing_period=recurring_billing_period,
    )
    ProductSEO.objects.create(product=product)

    dispatcher_product_created(product)
    return product


def dispatcher_product_created(product: Product) -> None:
    from core.events import dispatcher

    dispatcher.dispatch(
        ProductCreated(
            product_id=str(product.id), name=product.name, store_id=str(product.store_id)
        )
    )


def update_product(product: Product, **fields) -> Product:
    allowed = {
        "name",
        "description",
        "category",
        "brand",
        "price",
        "compare_at_price",
        "stock_quantity",
        "recurring_billing_period",
        "vendor",
    }
    unknown = set(fields) - allowed
    if unknown:
        raise ValidationError(f"Unknown fields: {', '.join(sorted(unknown))}", code="catalog.unknown_field")
    for key, value in fields.items():
        setattr(product, key, value)
    product.save()
    ProductSEO.objects.get_or_create(product=product)
    return product


def publish_product(product: Product) -> Product:
    _validate_product(product)
    product.is_published = True
    product.published_at = timezone.now()
    product.save(update_fields=["is_published", "published_at"])

    from core.events import dispatcher

    dispatcher.dispatch(ProductPublished(product_id=str(product.id), name=product.name))
    return product


def unpublish_product(product: Product) -> Product:
    product.is_published = False
    product.save(update_fields=["is_published"])
    return product


def add_variant(product: Product, sku: str, price, **kwargs) -> ProductVariant:
    if product.product_type != "variant":
        raise ValidationError(
            "Variants can only be added to variant products", code="catalog.not_variant_product"
        )
    if ProductVariant.objects.filter(sku=sku).exists():
        raise ConflictError(f"SKU {sku!r} already exists", code="catalog.sku_taken")
    return ProductVariant.objects.create(product=product, sku=sku, price=price, **kwargs)


def set_variant_attributes(variant: ProductVariant, attributes: dict) -> None:
    variant.attributes.all().delete()
    for attr_slug, value in attributes.items():
        attribute = ProductAttribute.objects.filter(slug=attr_slug).first()
        if attribute is None:
            attribute = ProductAttribute.objects.create(
                name=attr_slug.replace("_", " ").title(), slug=attr_slug
            )
        attr_value, _ = ProductAttributeValue.objects.get_or_create(
            attribute=attribute, value=value
        )
        from apps.catalog.models import ProductVariantAttribute

        ProductVariantAttribute.objects.create(
            variant=variant, attribute=attribute, value=attr_value
        )


def add_specification(product: Product, name: str, value: str) -> ProductSpecification:
    position = product.specifications.count()
    return ProductSpecification.objects.create(product=product, name=name, value=value, position=position)


def add_related_product(product: Product, related_product: Product, relation_type: str = "related"):
    if relation_type not in dict(RELATION_TYPES):
        raise ValidationError("Invalid relation type", code="catalog.invalid_relation_type")
    if related_product.id == product.id:
        raise ValidationError("A product cannot relate to itself", code="catalog.self_relation")
    relation, created = ProductRelation.objects.get_or_create(
        product=product, related_product=related_product, relation_type=relation_type
    )
    if not created:
        raise ConflictError("Relation already exists", code="catalog.relation_exists")
    return relation


def add_bundle_item(bundle: Product, child_product: Product, quantity: int = 1):
    if bundle.product_type != "bundled":
        raise ValidationError(
            "Bundle items can only be added to bundled products", code="catalog.not_bundled_product"
        )
    if child_product.id == bundle.id:
        raise ValidationError("A bundle cannot contain itself", code="catalog.self_bundle")
    item, created = ProductBundleItem.objects.get_or_create(
        bundle=bundle, child_product=child_product, defaults={"quantity": quantity}
    )
    if not created:
        raise ConflictError("Bundle item already exists", code="catalog.bundle_item_exists")
    return item


def attach_download(product: Product, file, label: str, max_downloads: int = 5) -> ProductDownload:
    if product.product_type not in ("digital", "downloadable"):
        raise ValidationError(
            "Downloads can only be attached to digital/downloadable products",
            code="catalog.not_downloadable",
        )
    return ProductDownload.objects.create(
        product=product, file=file, label=label, max_downloads=max_downloads
    )


def update_seo(product: Product, **fields) -> ProductSEO:
    seo, _ = ProductSEO.objects.get_or_create(product=product)
    allowed = {"meta_title", "meta_description", "canonical_url", "noindex"}
    unknown = set(fields) - allowed
    if unknown:
        raise ValidationError(f"Unknown SEO fields: {', '.join(sorted(unknown))}", code="catalog.unknown_field")
    for key, value in fields.items():
        setattr(seo, key, value)
    seo.save()
    return seo


def resolve_price(product: Product, variant: ProductVariant | None = None, context: dict | None = None):
    return pricing_registry.resolve(product, variant, context)


def _validate_typed_value(attribute: ProductAttribute, value) -> None:
    vtype = attribute.value_type

    if vtype == "boolean":
        if not isinstance(value, bool):
            raise ValidationError(f"Attribute {attribute.slug!r} requires a boolean", code="catalog.attr_type")
        return
    if vtype == "number":
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValidationError(f"Attribute {attribute.slug!r} requires a number", code="catalog.attr_type")
        return
    if vtype in ("text", "size"):
        if not isinstance(value, str) or not value.strip():
            raise ValidationError(f"Attribute {attribute.slug!r} requires text", code="catalog.attr_type")
        return
    if vtype == "color":
        if not isinstance(value, str) or not HEX_COLOR_RE.match(value):
            raise ValidationError(f"Attribute {attribute.slug!r} requires a hex color", code="catalog.attr_color")
        return
    if vtype == "select":
        if not ProductAttributeValue.objects.filter(attribute=attribute, value=value).exists():
            raise ValidationError(
                f"Value {value!r} is not a predefined option of {attribute.slug!r}",
                code="catalog.attr_option",
            )
        return
    if vtype == "multi_select":
        if not isinstance(value, list) or not value:
            raise ValidationError(f"Attribute {attribute.slug!r} requires a list", code="catalog.attr_type")
        existing = set(ProductAttributeValue.objects.filter(attribute=attribute).values_list("value", flat=True))
        unknown = [v for v in value if v not in existing]
        if unknown:
            raise ValidationError(
                f"Unknown options for {attribute.slug!r}: {', '.join(map(str, unknown))}",
                code="catalog.attr_option",
            )
        return
    raise ValidationError(f"Unknown attribute type {vtype!r}", code="catalog.attr_type")


def set_product_attribute(product: Product, attribute_slug: str, value) -> ProductAttributeAssignment:
    attribute = ProductAttribute.objects.filter(slug=attribute_slug).first()
    if attribute is None:
        attribute = ProductAttribute.objects.create(
            name=attribute_slug.replace("_", " ").title(), slug=attribute_slug
        )
    _validate_typed_value(attribute, value)
    assignment, _ = ProductAttributeAssignment.objects.update_or_create(
        product=product, attribute=attribute, defaults={"value": value}
    )
    return assignment


def get_product_attributes(product: Product) -> dict:
    return {
        a.attribute.slug: a.value
        for a in product.attribute_assignments.select_related("attribute")
    }
