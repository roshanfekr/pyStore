from django.conf import settings

from apps.catalog.models import Category
from apps.search.backends import (
    DatabaseSearchBackend,
    PostgresSearchBackend,
    SearchResult,
)

DEFAULT_BACKEND = "database"


class SearchBackendRegistry:
    def __init__(self):
        self._backends: dict = {}

    def register(self, name: str, backend) -> None:
        self._backends[name] = backend

    def get(self, name: str):
        backend = self._backends.get(name)
        if backend is None:
            raise KeyError(f"Search backend {name!r} is not registered")
        return backend

    def active(self):
        name = getattr(settings, "SEARCH_BACKEND", DEFAULT_BACKEND)
        try:
            return self.get(name)
        except KeyError:
            return self.get(DEFAULT_BACKEND)


search_backend_registry = SearchBackendRegistry()
search_backend_registry.register("database", DatabaseSearchBackend())
search_backend_registry.register("postgres", PostgresSearchBackend())


class SearchService:
    def __init__(self, backend=None):
        self._backend = backend

    @property
    def backend(self):
        if self._backend is None:
            self._backend = search_backend_registry.active()
        return self._backend

    def search_products(self, query="", **kwargs) -> SearchResult:
        return self.backend.search_products(query, **kwargs)

    def search_categories(self, query: str, limit: int = 10):
        if not query:
            return []
        return list(
            Category.objects.filter(name__icontains=query, is_active=True)[:limit]
        )

    def autocomplete(self, query: str, *, store=None, limit: int = 8) -> list[dict]:
        result = self.search_products(query, store=store, page=1, page_size=limit, ordering="name")
        return [
            {
                "name": product.name,
                "slug": product.slug,
                "price": str(product.price) if product.price else None,
            }
            for product in result.products
        ]

    def suggest(self, query: str, *, store=None, limit: int = 6) -> list[str]:
        suggestions: list[str] = []
        for category in self.search_categories(query, limit=limit):
            if category.name.lower() not in suggestions:
                suggestions.append(category.name)

        result = self.search_products(query, store=store, page=1, page_size=limit)
        for product in result.products:
            if product.name.lower() not in [s.lower() for s in suggestions]:
                suggestions.append(product.name)
        return suggestions[:limit]

    def index_product(self, product) -> None:
        self.backend.index_product(product)

    def remove_product(self, product_id) -> None:
        self.backend.remove_product(product_id)

    def reindex_all(self) -> int:
        return self.backend.reindex_all()


search_service = SearchService()
