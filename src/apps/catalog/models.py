
from django.db import models

from core.models import BaseModel

PRODUCT_TYPE_CHOICES = [
    ("simple", "Simple"),
    ("variant", "Variant"),
    ("digital", "Digital"),
    ("downloadable", "Downloadable"),
    ("recurring", "Recurring"),
    ("bundled", "Bundled"),
]

DIGITAL_TYPES = {"digital", "downloadable"}
RECURRING_PERIODS = [("weekly", "Weekly"), ("monthly", "Monthly"), ("yearly", "Yearly")]

RELATION_TYPES = [
    ("related", "Related"),
    ("cross_sell", "Cross-sell"),
    ("upsell", "Upsell"),
]


class Category(BaseModel):
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    description = models.TextField(blank=True)
    parent = models.ForeignKey(
        "self", null=True, blank=True, related_name="children", on_delete=models.CASCADE
    )
    is_active = models.BooleanField(default=True)
    ordering = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"
        ordering = ["ordering", "name"]

    def __str__(self):
        return self.name

    def ancestors(self):
        result = []
        current = self.parent
        depth = 0
        while current is not None and depth < 50:
            result.append(current)
            current = current.parent
            depth += 1
        return list(reversed(result))

    def descendant_ids(self):
        ids = []
        frontier = [self.id]
        depth = 0
        while frontier and depth < 50:
            next_ids = list(
                Category.objects.filter(parent_id__in=frontier).values_list("id", flat=True)
            )
            ids.extend(next_ids)
            frontier = next_ids
            depth += 1
        return ids


class Brand(BaseModel):
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Brand"
        verbose_name_plural = "Brands"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Tag(BaseModel):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)

    class Meta:
        verbose_name = "Tag"
        verbose_name_plural = "Tags"

    def __str__(self):
        return self.name


class Product(BaseModel):
    store = models.ForeignKey("stores.Store", related_name="products", on_delete=models.PROTECT)
    vendor = models.ForeignKey(
        "vendors.Vendor", null=True, blank=True, related_name="products", on_delete=models.SET_NULL
    )
    category = models.ForeignKey(
        Category, null=True, blank=True, related_name="products", on_delete=models.SET_NULL
    )
    brand = models.ForeignKey(
        Brand, null=True, blank=True, related_name="products", on_delete=models.SET_NULL
    )
    name = models.CharField(max_length=300)
    slug = models.SlugField(max_length=300, unique=True)
    description = models.TextField(blank=True)
    product_type = models.CharField(max_length=20, choices=PRODUCT_TYPE_CHOICES, default="simple")

    price = models.DecimalField(
        max_digits=18, decimal_places=4, null=True, blank=True
    )
    compare_at_price = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    stock_quantity = models.PositiveIntegerField(default=0)

    sku = models.CharField(max_length=100, blank=True)
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)

    recurring_billing_period = models.CharField(
        max_length=10, choices=RECURRING_PERIODS, null=True, blank=True
    )

    tags = models.ManyToManyField(Tag, related_name="products", blank=True)

    class Meta:
        verbose_name = "Product"
        verbose_name_plural = "Products"
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    @property
    def is_digital(self) -> bool:
        return self.product_type in DIGITAL_TYPES


class ProductVariant(BaseModel):
    product = models.ForeignKey(Product, related_name="variants", on_delete=models.CASCADE)
    sku = models.CharField(max_length=100, unique=True)
    price = models.DecimalField(max_digits=18, decimal_places=4)
    compare_at_price = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    stock_quantity = models.PositiveIntegerField(default=0)
    weight = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    length = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    width = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    height = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Product variant"
        verbose_name_plural = "Product variants"
        ordering = ["sku"]

    def __str__(self):
        return self.sku


ATTRIBUTE_VALUE_TYPES = [
    ("text", "Text"),
    ("number", "Number"),
    ("boolean", "Boolean"),
    ("select", "Select"),
    ("multi_select", "Multi-select"),
    ("color", "Color"),
    ("size", "Size"),
]


class ProductAttribute(BaseModel):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)
    value_type = models.CharField(max_length=20, choices=ATTRIBUTE_VALUE_TYPES, default="text")
    is_variant_option = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Product attribute"
        verbose_name_plural = "Product attributes"

    def __str__(self):
        return self.name


class ProductAttributeAssignment(models.Model):
    product = models.ForeignKey(
        Product, related_name="attribute_assignments", on_delete=models.CASCADE
    )
    attribute = models.ForeignKey(
        ProductAttribute, related_name="product_assignments", on_delete=models.CASCADE
    )
    value = models.JSONField()

    class Meta:
        verbose_name = "Product attribute assignment"
        verbose_name_plural = "Product attribute assignments"
        constraints = [
            models.UniqueConstraint(
                fields=["product", "attribute"], name="uniq_product_attribute"
            ),
        ]

    def __str__(self):
        return f"{self.product_id}:{self.attribute.slug}"


class ProductAttributeValue(models.Model):
    attribute = models.ForeignKey(
        ProductAttribute, related_name="values", on_delete=models.CASCADE
    )
    value = models.CharField(max_length=255)
    position = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Product attribute value"
        verbose_name_plural = "Product attribute values"
        ordering = ["attribute", "position"]

    def __str__(self):
        return f"{self.attribute.slug}: {self.value}"


class ProductVariantAttribute(models.Model):
    variant = models.ForeignKey(
        ProductVariant, related_name="attributes", on_delete=models.CASCADE
    )
    attribute = models.ForeignKey(
        ProductAttribute, related_name="variant_attributes", on_delete=models.CASCADE
    )
    value = models.ForeignKey(
        ProductAttributeValue, related_name="variant_links", on_delete=models.CASCADE
    )

    class Meta:
        verbose_name = "Variant attribute"
        verbose_name_plural = "Variant attributes"
        constraints = [
            models.UniqueConstraint(
                fields=["variant", "attribute"], name="uniq_variant_attribute"
            ),
        ]


class ProductSpecification(models.Model):
    product = models.ForeignKey(
        Product, related_name="specifications", on_delete=models.CASCADE
    )
    name = models.CharField(max_length=200)
    value = models.CharField(max_length=500)
    position = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Product specification"
        verbose_name_plural = "Product specifications"
        ordering = ["position"]


class ProductImage(models.Model):
    product = models.ForeignKey(Product, related_name="images", on_delete=models.CASCADE)
    image = models.ImageField(upload_to="catalog/products/%Y/%m/")
    alt_text = models.CharField(max_length=300, blank=True)
    position = models.PositiveIntegerField(default=0)
    is_main = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Product image"
        verbose_name_plural = "Product images"
        ordering = ["position"]

    def save(self, *args, **kwargs):
        if self.is_main:
            ProductImage.objects.filter(product=self.product).exclude(pk=self.pk).update(
                is_main=False
            )
        super().save(*args, **kwargs)


class ProductRelation(models.Model):
    product = models.ForeignKey(
        Product, related_name="relations", on_delete=models.CASCADE
    )
    related_product = models.ForeignKey(
        Product, related_name="relations_to", on_delete=models.CASCADE
    )
    relation_type = models.CharField(max_length=20, choices=RELATION_TYPES, default="related")
    position = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Product relation"
        verbose_name_plural = "Product relations"
        ordering = ["position"]
        constraints = [
            models.UniqueConstraint(
                fields=["product", "related_product", "relation_type"],
                name="uniq_product_relation",
            ),
        ]


class ProductDownload(models.Model):
    product = models.ForeignKey(Product, related_name="downloads", on_delete=models.CASCADE)
    file = models.FileField(upload_to="catalog/downloads/%Y/%m/")
    label = models.CharField(max_length=200)
    max_downloads = models.PositiveIntegerField(default=5)
    position = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Product download"
        verbose_name_plural = "Product downloads"
        ordering = ["position"]


class ProductBundleItem(models.Model):
    bundle = models.ForeignKey(
        Product, related_name="bundle_items", on_delete=models.CASCADE
    )
    child_product = models.ForeignKey(
        Product, related_name="bundle_in", on_delete=models.CASCADE
    )
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        verbose_name = "Bundle item"
        verbose_name_plural = "Bundle items"
        constraints = [
            models.UniqueConstraint(
                fields=["bundle", "child_product"], name="uniq_bundle_item"
            ),
        ]


class ProductSEO(models.Model):
    product = models.OneToOneField(Product, related_name="seo", on_delete=models.CASCADE)
    meta_title = models.CharField(max_length=200, blank=True)
    meta_description = models.CharField(max_length=300, blank=True)
    canonical_url = models.CharField(max_length=500, blank=True)
    noindex = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Product SEO"
        verbose_name_plural = "Product SEO"

    def __str__(self):
        return f"SEO for {self.product_id}"
