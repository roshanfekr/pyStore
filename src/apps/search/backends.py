from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from django.db.models import Q

from apps.catalog.models import Product, ProductVariant
from apps.inventory.models import InventoryItem


@dataclass
class SearchResult:
    products: list = field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 12
    total_pages: int = 0
    query: str = ""


class SearchBackend(ABC):
    """Adapter contract — swap for Elasticsearch/OpenSearch later."""

    name = "base"

    @abstractmethod
    def search_products(self, query: str, **kwargs) -> SearchResult:
        ...

    @abstractmethod
    def index_product(self, product) -> None:
        ...

    @abstractmethod
    def remove_product(self, product_id) -> None:
        ...

    @abstractmethod
    def reindex_all(self) -> int:
        ...


def available_quantity_for(product: Product, variant: ProductVariant | None) -> int | None:
    if product.product_type in ("digital", "downloadable"):
        return None
    if variant is not None:
        items = InventoryItem.objects.filter(variant=variant)
    else:
        items = InventoryItem.objects.filter(product=product)
    if items.exists():
        return sum(item.available_quantity for item in items)
    if variant is not None:
        return variant.stock_quantity
    return product.stock_quantity


class DatabaseSearchBackend(SearchBackend):
    """Portable backend: icontains matching on every database (SQLite included)."""

    name = "database"

    def search_products(self, query: str, **kwargs) -> SearchResult:
        store = kwargs.get("store")
        category = kwargs.get("category")
        brand = kwargs.get("brand")
        min_price = kwargs.get("min_price")
        max_price = kwargs.get("max_price")
        in_stock = kwargs.get("in_stock", False)
        ordering = kwargs.get("ordering", "-created_at")
        page = max(int(kwargs.get("page") or 1), 1)
        page_size = min(max(int(kwargs.get("page_size") or 12), 1), 100)

        queryset = Product.objects.filter(is_published=True).select_related("category", "brand")
        if store is not None:
            queryset = queryset.filter(store=store)
        if query:
            from apps.catalog.models import Category

            matching_category_ids: set = set()
            for category in Category.objects.filter(name__icontains=query):
                matching_category_ids.add(category.id)
                matching_category_ids.update(category.descendant_ids())

            queryset = queryset.filter(
                Q(name__icontains=query)
                | Q(description__icontains=query)
                | Q(brand__name__icontains=query)
                | Q(category_id__in=matching_category_ids)
            )
        if category is not None:
            queryset = queryset.filter(category_id__in=[category.id, *category.descendant_ids()])
        if brand is not None:
            queryset = queryset.filter(brand=brand)
        if min_price is not None:
            queryset = queryset.filter(price__gte=min_price)
        if max_price is not None:
            queryset = queryset.filter(price__lte=max_price)

        if in_stock:
            in_stock_ids = [
                product.id
                for product in queryset
                if (available_quantity_for(product, None) or 0) > 0
            ]
            queryset = queryset.filter(id__in=in_stock_ids)

        orderings = {
            "price_asc": ["price"],
            "price_desc": ["-price"],
            "name": ["name"],
            "newest": ["-created_at"],
        }
        queryset = queryset.order_by(*orderings.get(ordering, ["-created_at"]))

        total = queryset.count()
        total_pages = (total + page_size - 1) // page_size
        page_items = list(queryset[(page - 1) * page_size : page * page_size])

        return SearchResult(
            products=page_items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            query=query,
        )

    def index_product(self, product) -> None:
        return None

    def remove_product(self, product_id) -> None:
        return None

    def reindex_all(self) -> int:
        return Product.objects.filter(is_published=True).count()


class PostgresSearchBackend(DatabaseSearchBackend):
    """PostgreSQL full-text search (tsvector ranking). Requires PostgreSQL."""

    name = "postgres"

    def search_products(self, query: str, **kwargs) -> SearchResult:
        if not query:
            return super().search_products(query, **kwargs)

        from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector

        vector = SearchVector("name", weight="A") + SearchVector("description", weight="B")
        search_query = SearchQuery(query)

        base = self._filtered_queryset(kwargs)
        queryset = (
            base.annotate(search=vector, rank=SearchRank(vector, search_query))
            .filter(search=search_query)
            .order_by("-rank")
        )

        page = max(int(kwargs.get("page") or 1), 1)
        page_size = min(max(int(kwargs.get("page_size") or 12), 1), 100)
        total = queryset.count()
        total_pages = (total + page_size - 1) // page_size

        return SearchResult(
            products=list(queryset[(page - 1) * page_size : page * page_size]),
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            query=query,
        )

    def _filtered_queryset(self, kwargs):
        queryset = Product.objects.filter(is_published=True).select_related("category", "brand")
        store = kwargs.get("store")
        if store is not None:
            queryset = queryset.filter(store=store)
        return queryset
