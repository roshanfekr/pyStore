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


def test_dropdown_menu_escapes_ancestor_clipping():
    # Django's ``forms.css`` sets ``.form-row { overflow: hidden }`` which used to
    # clip the lower half of the combobox menu. The fix detaches the menu to
    # <body> and positions it with ``position: fixed`` so no ancestor's overflow
    # can clip it.
    from django.contrib.staticfiles import finders

    js_path = finders.find("admin_panel/js/searchable_select.js")
    css_path = finders.find("admin_panel/admin.css")
    assert js_path and css_path

    with open(js_path, encoding="utf-8") as handle:
        js = handle.read()
    with open(css_path, encoding="utf-8") as handle:
        css = handle.read()

    # The menu is attached to the body (outside any clipping container)...
    assert "document.body.appendChild(menu)" in js
    # ...and positioned as a fixed overlay with an explicit high z-index.
    assert "menu.style.position = 'fixed'" in js
    assert "position: fixed;" in css
    # Django's ``forms.css`` (loaded after admin.css) forces
    # ``.form-row { overflow: hidden }``, so the override must use ``!important``
    # to win the cascade.
    assert ".form-row:has(.ps-select) { overflow: visible !important; }" in css
