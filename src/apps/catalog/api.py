from django.utils.text import slugify
from rest_framework import serializers, status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from apps.catalog.models import Brand, Category, Product
from apps.catalog.services import (
    create_product,
    publish_product,
    unpublish_product,
    update_product,
)
from apps.identity.api import has_perm
from core.api.filters import QueryParamFilterMixin
from core.exceptions import NotFoundError


def unique_slug(model, name: str) -> str:
    base = slugify(name)[:180] or "item"
    slug = base
    index = 2
    while model.objects.filter(slug=slug).exists():
        slug = f"{base}-{index}"
        index += 1
    return slug


def _ensure_slug(serializer: serializers.ModelSerializer, validated_data: dict) -> dict:
    if not validated_data.get("slug"):
        validated_data["slug"] = unique_slug(serializer.Meta.model, validated_data.get("name", ""))
    return validated_data


class CategorySerializer(serializers.ModelSerializer):
    parent = serializers.SlugRelatedField(
        slug_field="slug", queryset=Category.objects.all(), required=False, allow_null=True
    )

    class Meta:
        model = Category
        fields = ["id", "name", "slug", "description", "parent", "is_active", "ordering"]
        read_only_fields = ["slug"]

    def create(self, validated_data):
        return super().create(_ensure_slug(self, validated_data))


class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = ["id", "name", "slug", "description", "is_active"]
        read_only_fields = ["slug"]

    def create(self, validated_data):
        return super().create(_ensure_slug(self, validated_data))


class ProductSerializer(serializers.ModelSerializer):
    category = serializers.SlugRelatedField(
        slug_field="slug", queryset=Category.objects.all(), required=False, allow_null=True
    )
    brand = serializers.SlugRelatedField(
        slug_field="slug", queryset=Brand.objects.all(), required=False, allow_null=True
    )

    class Meta:
        model = Product
        fields = [
            "id", "store", "name", "slug", "description", "product_type",
            "category", "brand", "price", "compare_at_price", "stock_quantity",
            "sku", "is_published",
        ]
        read_only_fields = ["slug", "is_published", "store"]


class ProductViewSet(QueryParamFilterMixin, ModelViewSet):
    serializer_class = ProductSerializer
    lookup_field = "slug"
    permission_classes = [AllowAny]

    query_filters = {
        "store": "store__slug",
        "category": "category__slug",
        "brand": "brand__slug",
        "product_type": "product_type",
        "is_published": "is_published",
        "price_min": "price__gte",
        "price_max": "price__lte",
    }
    ordering_fields = ("price", "name", "created_at")
    search_fields = ("name", "description", "sku")
    default_ordering = "-created_at"

    def get_queryset(self):
        queryset = Product.objects.select_related("store", "category", "brand")
        user = self.request.user
        is_staff_view = self.action != "list" and self.action != "retrieve"
        if is_staff_view:
            return queryset
        if user.is_authenticated and user.has_perm("catalog.product.view"):
            return queryset
        return queryset.filter(is_published=True)

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [AllowAny()]
        if self.action == "create":
            return [IsAuthenticated(), has_perm("catalog.product.create")()]
        if self.action in ("update", "partial_update", "publish", "unpublish"):
            return [IsAuthenticated(), has_perm("catalog.product.update")()]
        if self.action == "destroy":
            return [IsAuthenticated(), has_perm("catalog.product.delete")()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        data = dict(serializer.validated_data)
        store_slug = self.request.data.get("store")
        store = None
        if store_slug:
            from apps.stores.models import Store

            store = Store.objects.filter(slug=store_slug).first()
        if store is None:
            from apps.stores.services import ensure_default_store

            store = ensure_default_store()
        product = create_product(
            store,
            data["name"],
            category=data.get("category"),
            brand=data.get("brand"),
            product_type=data.get("product_type", "simple"),
            price=data.get("price"),
            compare_at_price=data.get("compare_at_price"),
            description=data.get("description", ""),
            sku=data.get("sku", ""),
            stock_quantity=data.get("stock_quantity", 0),
        )
        serializer.instance = product

    def perform_update(self, serializer):
        product = serializer.instance
        data = {key: value for key, value in serializer.validated_data.items()}
        update_product(product, **data)

    def destroy(self, request, *args, **kwargs):
        product = self.get_object()
        product.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def _require_product(self) -> Product:
        product = Product.objects.filter(slug=self.kwargs.get("slug")).first()
        if product is None:
            raise NotFoundError("Product not found", code="catalog.product_not_found")
        return product

    @action(detail=True, methods=["post"])
    def publish(self, request, *args, **kwargs):
        product = publish_product(self._require_product())
        return Response(ProductSerializer(product).data)

    @action(detail=True, methods=["post"])
    def unpublish(self, request, *args, **kwargs):
        product = unpublish_product(self._require_product())
        return Response(ProductSerializer(product).data)


class CategoryViewSet(QueryParamFilterMixin, ModelViewSet):
    serializer_class = CategorySerializer
    lookup_field = "slug"
    query_filters = {"parent": "parent__slug", "is_active": "is_active"}
    ordering_fields = ("name", "ordering", "created_at")
    search_fields = ("name", "description")
    default_ordering = "ordering,name"

    def get_queryset(self):
        return Category.objects.all()

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [AllowAny()]
        return [IsAuthenticated(), has_perm("catalog.category.manage")()]


class BrandViewSet(QueryParamFilterMixin, ModelViewSet):
    serializer_class = BrandSerializer
    lookup_field = "slug"
    query_filters = {"is_active": "is_active"}
    ordering_fields = ("name", "created_at")
    search_fields = ("name",)
    default_ordering = "name"

    def get_queryset(self):
        return Brand.objects.all()

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [AllowAny()]
        return [IsAuthenticated(), has_perm("catalog.brand.manage")()]
