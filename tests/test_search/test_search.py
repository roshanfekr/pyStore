from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.catalog.models import Brand, Category
from apps.catalog.services import create_product, publish_product
from apps.inventory.services import create_warehouse, get_or_create_inventory, receive_stock
from apps.search.service import SearchService, search_backend_registry, search_service
from apps.stores.services import create_store

User = get_user_model()

pytestmark = [pytest.mark.django_db]


@pytest.fixture
def store(db):
    return create_store("Search Store")


@pytest.fixture
def service(db):
    return SearchService()


@pytest.fixture
def catalog_data(store):
    electronics = Category.objects.create(name="Electronics", slug="electronics")
    laptops = Category.objects.create(name="Laptops", slug="laptops", parent=electronics)

    brand_a = Brand.objects.create(name="TechnoBrand", slug="technobrand")
    brand_b = Brand.objects.create(name="OtherBrand", slug="otherbrand")

    laptop = create_product(
        store, "Gaming Laptop", price=Decimal("900.0000"), category=laptops,
        brand=brand_a, description="A powerful gaming laptop",
    )
    publish_product(laptop)

    phone = create_product(
        store, "Smart Phone", price=Decimal("400.0000"), category=electronics,
        brand=brand_b, description="A phone with camera",
    )
    publish_product(phone)

    hidden = create_product(store, "Hidden Laptop", price=Decimal("500.0000"))
    draft = create_product(store, "Draft Phone", price=Decimal("10.0000"))

    return {"electronics": electronics, "laptops": laptops, "laptop": laptop, "phone": phone,
            "hidden": hidden, "draft": draft, "brand_a": brand_a, "brand_b": brand_b}


def test_full_text_search_by_name(service, catalog_data):
    result = service.search_products("gaming")
    names = [p.name for p in result.products]
    assert "Gaming Laptop" in names
    assert "Smart Phone" not in names


def test_search_by_description(service, catalog_data):
    result = service.search_products("camera")
    assert [p.name for p in result.products] == ["Smart Phone"]


def test_search_by_category_name(service, catalog_data):
    result = service.search_products("electronics")
    names = [p.name for p in result.products]
    assert "Gaming Laptop" in names
    assert "Smart Phone" in names


def test_search_only_published(service, catalog_data):
    result = service.search_products("laptop")
    names = [p.name for p in result.products]
    assert "Hidden Laptop" not in names


def test_search_scoped_to_store(service, catalog_data, store):
    other = create_store("Other Search Store")
    foreign = create_product(other, "Gaming Laptop Foreign", price=Decimal("100.0000"))
    publish_product(foreign)

    scoped = service.search_products("gaming", store=store)
    assert all(p.store_id == store.id for p in scoped.products)


def test_empty_query_returns_all_published(service, catalog_data):
    result = service.search_products("")
    assert result.total == 2


def test_category_filter_includes_descendants(service, catalog_data):
    result = service.search_products("", category=catalog_data["electronics"])
    names = [p.name for p in result.products]
    assert "Gaming Laptop" in names
    assert "Smart Phone" in names

    only_laptops = service.search_products("", category=catalog_data["laptops"])
    assert [p.name for p in only_laptops.products] == ["Gaming Laptop"]


def test_brand_filter(service, catalog_data):
    result = service.search_products("", brand=catalog_data["brand_a"])
    assert [p.name for p in result.products] == ["Gaming Laptop"]


def test_price_range_filter(service, catalog_data):
    result = service.search_products("", min_price=Decimal("500.0000"))
    assert [p.name for p in result.products] == ["Gaming Laptop"]

    both = service.search_products("", min_price=Decimal("300.0000"), max_price=Decimal("950.0000"))
    assert both.total == 2


def test_in_stock_filter_with_inventory(service, catalog_data, store):
    catalog_data["laptop"].stock_quantity = 5
    catalog_data["laptop"].save()

    warehouse = create_warehouse(store, "Search WH", "WH-S")
    item = get_or_create_inventory(warehouse, product=catalog_data["phone"])

    out_of_stock = service.search_products("", in_stock=True)
    assert [p.name for p in out_of_stock.products] == ["Gaming Laptop"]

    receive_stock(item, 4)
    result = service.search_products("", in_stock=True)
    assert result.total == 2


def test_in_stock_filter_fallback_to_stock_field(service, catalog_data):
    catalog_data["laptop"].stock_quantity = 0
    catalog_data["laptop"].save()
    catalog_data["phone"].stock_quantity = 3
    catalog_data["phone"].save()

    result = service.search_products("", in_stock=True)
    assert [p.name for p in result.products] == ["Smart Phone"]


def test_sorting(service, catalog_data):
    by_price = service.search_products("", ordering="price_asc")
    assert [p.name for p in by_price.products] == ["Smart Phone", "Gaming Laptop"]

    by_price_desc = service.search_products("", ordering="price_desc")
    assert [p.name for p in by_price_desc.products] == ["Gaming Laptop", "Smart Phone"]

    by_name = service.search_products("", ordering="name")
    assert [p.name for p in by_name.products] == ["Gaming Laptop", "Smart Phone"]


def test_pagination(service, catalog_data):
    bulk_store = catalog_data["laptop"].store
    for index in range(15):
        product = create_product(bulk_store, f"Bulk {index}", price=Decimal("1.0000"))
        publish_product(product)

    page1 = service.search_products("bulk", page=1, page_size=10)
    assert page1.total == 15
    assert page1.total_pages == 2
    assert len(page1.products) == 10

    page2 = service.search_products("bulk", page=2, page_size=10)
    assert len(page2.products) == 5

    beyond = service.search_products("bulk", page=9, page_size=10)
    assert beyond.products == []


def test_autocomplete(service, catalog_data, store):
    results = search_service.autocomplete("gaming", store=store)
    assert len(results) == 1
    assert results[0]["name"] == "Gaming Laptop"
    assert results[0]["slug"] == "gaming-laptop"
    assert results[0]["price"] == "900.0000"


def test_suggestions_include_categories(service, catalog_data):
    suggestions = search_service.suggest("electron")
    assert "Electronics" in suggestions


def test_category_search(service, catalog_data):
    categories = service.search_categories("laptop")
    assert [c.name for c in categories] == ["Laptops"]


def test_backend_registry_and_adapters(db):
    assert search_backend_registry.get("database") is not None
    assert search_backend_registry.get("postgres") is not None
    assert search_backend_registry.active().name == "database"

    with pytest.raises(KeyError):
        search_backend_registry.get("elasticsearch")

    search_backend_registry.register("elasticsearch", search_backend_registry.get("database"))
    assert search_backend_registry.get("elasticsearch") is not None


def test_index_operations_are_safe_noops_for_database_backend(service, catalog_data):
    service.index_product(catalog_data["laptop"])
    service.remove_product("missing-id")
    assert service.reindex_all() == 2


def test_indexing_task_runs_in_background(db, catalog_data):
    from apps.search.tasks import index_product_task, reindex_search_task

    assert index_product_task.delay(str(catalog_data["laptop"].id)).get() is True
    assert index_product_task.delay("00000000-0000-0000-0000-000000000000").get() is False
    assert reindex_search_task.delay().get() == 2


def test_postgres_backend_class_available():
    from apps.search.backends import PostgresSearchBackend

    backend = PostgresSearchBackend()
    assert backend.name == "postgres"
