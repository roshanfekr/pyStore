from decimal import Decimal

import pytest

from apps.catalog.models import ProductVariant
from apps.catalog.services import create_product
from apps.stores.services import create_store
from tests.test_admin.test_inline_dialog import _base_product_data, _change_url, _empty_management

pytestmark = [pytest.mark.django_db]


@pytest.fixture
def admin_user(db):
    from apps.identity.models import User

    return User.objects.create_superuser(email="root@example.com", password="Str0ng!Passw0rd")


@pytest.fixture
def product(db):
    store = create_store("Debug Store")
    return create_product(store, "Debug Product", price=Decimal("10.0000"))


def test_debug_admin_post(client, admin_user, product):
    client.force_login(admin_user)
    data = _base_product_data(product)
    data.update(_empty_management("variants"))
    data.update(_empty_management("specifications"))
    data.update(_empty_management("seo"))
    data.update(_empty_management("productprices"))
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
    if response.status_code != 302:
        context = response.context
        adminform = context.get("adminform")
        print("ADMINFORM ERRORS:", adminform.form.errors if adminform else None)
        inline_admin_formsets = getattr(adminform, "inline_admin_formsets", []) if adminform else []
        for inline in inline_admin_formsets:
            print("INLINE:", inline.opts.verbose_name, "errors:", inline.formset.errors)
        print("FORMSET NONFORM ERRORS:", [getattr(i.formset, "non_form_errors", lambda: [])() for i in inline_admin_formsets])
    assert response.status_code == 302
