"""Tests for the dialog-based product inlines.

The three product inlines (variants, specifications, SEO) are rendered as a
read-only grid plus a Bootstrap dialog instead of Django's default inline table.
The visible grid is a client-side view of the real (hidden) formset, so these
tests cover both the rendered markup and the fact that the underlying formset
still saves/deletes rows through the normal admin form.
"""

import pytest
from django.contrib.auth import get_user_model

from apps.catalog.models import ProductSpecification, ProductVariant
from apps.catalog.services import create_product

User = get_user_model()

pytestmark = [pytest.mark.django_db]


@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser(email="dialog@example.com", password="Str0ng!Passw0rd")


@pytest.fixture
def store(db):
    from apps.stores.services import create_store

    return create_store("Dialog Store")


@pytest.fixture
def product(store):
    return create_product(store, "Dialog Product", price="10.00")


@pytest.fixture
def variant(product):
    return ProductVariant.objects.create(product=product, sku="VAR-1", price="11.0000")


def _change_url(product):
    return f"/admin/catalog/product/{product.pk}/change/"


def _base_product_data(product):
    """Minimum valid POST data for the Product admin form."""
    return {
        "store": product.store_id,
        "vendor": "",
        "category": "",
        "brand": "",
        "name": product.name,
        "slug": product.slug,
        "description": "",
        "product_type": "simple",
        "price": "10.0000",
        "compare_at_price": "",
        "stock_quantity": "0",
        "sku": "",
        "is_published": "",
        "recurring_billing_period": "",
        "tags_input": "",
        "published_at_0": "",
        "published_at_1": "",
    }


def _empty_management(prefix):
    return {
        f"{prefix}-TOTAL_FORMS": "0",
        f"{prefix}-INITIAL_FORMS": "0",
        f"{prefix}-MIN_NUM_FORMS": "0",
        f"{prefix}-MAX_NUM_FORMS": "1000",
    }


def test_inlines_use_dialog_template():
    from apps.admin_panel.registrations import (
        INLINE_DIALOG_TEMPLATE,
        ProductSEOInline,
        ProductSpecificationInline,
        ProductVariantInline,
    )

    for inline in (ProductVariantInline, ProductSpecificationInline, ProductSEOInline):
        assert inline.template == INLINE_DIALOG_TEMPLATE


def test_change_form_renders_dialog_grids(client, admin_user, product, variant):
    client.force_login(admin_user)
    content = client.get(_change_url(product)).content.decode()

    # One dialog grid per inline, each with an Add button and its own modal.
    assert content.count("data-ps-inline") >= 3
    assert "data-ps-inline-add" in content
    assert 'id="ps-inline-modal-variants"' in content
    assert 'id="ps-inline-modal-specifications"' in content
    assert 'id="ps-inline-modal-seo"' in content
    # The external (CSP-safe) script drives the dialogs.
    assert "admin_panel/js/inline_dialog.js" in content


def test_grid_shows_existing_rows_with_edit_and_delete(client, admin_user, product, variant):
    client.force_login(admin_user)
    content = client.get(_change_url(product)).content.decode()

    # The saved variant is rendered as a grid row with edit/delete controls.
    assert "ps-inline-row" in content
    assert "ps-inline-edit" in content
    assert "ps-inline-delete-btn" in content
    assert 'data-ps-field="variants-0-sku"' in content
    # The hidden, always-submitted formset form carries the real input.
    assert 'name="variants-0-sku"' in content
    assert 'value="VAR-1"' in content


def test_adding_row_through_formset_creates_variant(client, admin_user, product):
    client.force_login(admin_user)
    data = _base_product_data(product)
    data.update(_empty_management("variants"))
    data.update(_empty_management("specifications"))
    data.update(_empty_management("seo"))
    data.update(
        {
            "variants-TOTAL_FORMS": "1",
            "variants-0-sku": "NEW-SKU-1",
            "variants-0-price": "12.5000",
            "variants-0-compare_at_price": "",
            "variants-0-stock_quantity": "4",
            "variants-0-weight": "",
            "variants-0-length": "",
            "variants-0-width": "",
            "variants-0-height": "",
            "_save": "Save",
        }
    )

    response = client.post(_change_url(product), data)
    assert response.status_code == 302
    assert ProductVariant.objects.filter(product=product, sku="NEW-SKU-1").exists()


def test_delete_checkbox_removes_variant(client, admin_user, product, variant):
    client.force_login(admin_user)
    data = _base_product_data(product)
    data.update(_empty_management("specifications"))
    data.update(_empty_management("seo"))
    data.update(
        {
            "variants-TOTAL_FORMS": "1",
            "variants-INITIAL_FORMS": "1",
            "variants-0-id": str(variant.pk),
            "variants-0-sku": variant.sku,
            "variants-0-price": "11.0000",
            "variants-0-compare_at_price": "",
            "variants-0-stock_quantity": "0",
            "variants-0-weight": "",
            "variants-0-length": "",
            "variants-0-width": "",
            "variants-0-height": "",
            "variants-0-DELETE": "on",
            "_save": "Save",
        }
    )

    response = client.post(_change_url(product), data)
    assert response.status_code == 302
    assert not ProductVariant.objects.filter(pk=variant.pk).exists()


def test_specification_inline_is_wired_to_the_same_dialog(client, admin_user, product):
    ProductSpecification.objects.create(product=product, name="Color", value="Red", position=0)
    client.force_login(admin_user)
    content = client.get(_change_url(product)).content.decode()
    assert 'data-ps-field="specifications-0-name"' in content
    assert 'name="specifications-0-value"' in content


def test_variant_inline_hides_soft_delete_fields(client, admin_user, product, variant):
    """The soft-delete bookkeeping fields must not leak into the inline dialog.

    ``ProductVariant`` extends the soft-delete ``BaseModel``; removing a variant
    is done with the grid's Delete button, never by editing an "Is deleted"
    checkbox, so ``is_deleted``/``deleted_at`` are excluded from the inline.
    """
    client.force_login(admin_user)
    content = client.get(_change_url(product)).content.decode()
    assert 'name="variants-0-is_deleted"' not in content
    assert 'name="variants-0-deleted_at"' not in content
    # The row is still present and editable through the grid.
    assert 'data-ps-field="variants-0-sku"' in content
