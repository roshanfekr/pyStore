import pytest
from django.contrib.auth import get_user_model

from apps.admin_panel.widgets import SearchableSelectWidget
from apps.catalog.services import create_product

User = get_user_model()

pytestmark = [pytest.mark.django_db]


@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser(email="select@example.com", password="Str0ng!Passw0rd")


@pytest.fixture
def store(db):
    from apps.stores.services import create_store

    return create_store("Select Store")


@pytest.fixture
def product(store):
    return create_product(store, "Selectable Product", price="10.00")


def test_widget_marks_select_for_enhancement():
    widget = SearchableSelectWidget()
    html = widget.render("category", None, attrs={"id": "id_category"})
    assert 'class="ps-search-select"' in html
    assert "<select" in html


def test_widget_preserves_existing_classes():
    widget = SearchableSelectWidget(attrs={"class": "custom-select"})
    html = widget.render("category", None, attrs={"id": "id_category"})
    assert "ps-search-select custom-select" in html


def test_product_change_form_uses_searchable_select(client, admin_user, product):
    client.force_login(admin_user)
    content = client.get(f"/admin/catalog/product/{product.pk}/change/").content.decode()
    # The related-object selects (store/category/brand/vendor) are enhanced.
    assert "ps-search-select" in content
    assert "admin_panel/js/searchable_select.js" in content
