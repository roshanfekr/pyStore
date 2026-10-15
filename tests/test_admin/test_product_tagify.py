"""Tests for the Tagify-powered product tag input and asset wiring.

Regression coverage for three admin-panel defects:

1. The tag input is a free-text Tagify widget (``ps-tagify``) instead of the
   old inline-script picker.
2. ``product_images.js`` is loaded exactly once on the product change form
   (it used to be included both through ``ProductAdmin.Media`` and the
   template, which double-bound every event handler).
3. No inline ``<script>`` blocks are emitted for the tag picker, because the
   site Content-Security-Policy (``script-src 'self'``) blocks them.
"""

import re

import pytest
from django.contrib.auth import get_user_model

from apps.admin_panel.widgets import TagPickerWidget
from apps.catalog.models import Tag
from apps.catalog.services import create_product

User = get_user_model()

pytestmark = [pytest.mark.django_db]


@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser(email="tagify@example.com", password="Str0ng!Passw0rd")


@pytest.fixture
def store(db):
    from apps.stores.services import create_store

    return create_store("Tagify Store")


@pytest.fixture
def product(store):
    return create_product(store, "Tagify Product", price="10.00")


def test_widget_renders_tagify_marker_and_json_payload():
    Tag.objects.create(name="Alpha", slug="alpha")
    Tag.objects.create(name="Beta", slug="beta")
    widget = TagPickerWidget()
    html = widget.render("tags_input", "Alpha, Beta", attrs={"id": "id_tags_input"})
    # Marker class consumed by tagify_init.js.
    assert "ps-tagify" in html
    # The whitelist payload is emitted exactly once as a json_script element.
    assert 'id="id_tags_input_data"' in html
    assert html.count('type="application/json"') == 1
    # It must be valid JSON (a double-encoded string would break JSON.parse).
    import json

    payload = re.search(
        r'<script id="id_tags_input_data" type="application/json">(.*?)</script>',
        html,
        re.DOTALL,
    )
    assert payload is not None
    assert json.loads(payload.group(1)) == ["Alpha", "Beta"]


def test_widget_accepts_list_value():
    widget = TagPickerWidget()
    html = widget.render("tags_input", ["One", "Two"], attrs={"id": "id_tags_input"})
    assert 'value="One, Two"' in html


def test_change_form_loads_tagify_assets_once(client, admin_user, product):
    client.force_login(admin_user)
    content = client.get(f"/admin/catalog/product/{product.pk}/change/").content.decode()
    assert content.count("admin_panel/vendor/tagify/tagify.min.js") == 1
    assert content.count("admin_panel/js/tagify_init.js") == 1
    assert content.count("admin_panel/vendor/tagify/tagify.css") == 1
    assert content.count('class="ps-tagify"') == 1 or "ps-tagify" in content


def test_change_form_loads_product_images_script_once(client, admin_user, product):
    client.force_login(admin_user)
    content = client.get(f"/admin/catalog/product/{product.pk}/change/").content.decode()
    # The duplicate include (Media + template) used to double-bind the JS.
    assert content.count("admin_panel/js/product_images.js") == 1


def test_change_form_has_no_inline_scripts_for_tag_picker(client, admin_user, product):
    client.force_login(admin_user)
    content = client.get(f"/admin/catalog/product/{product.pk}/change/").content.decode()
    # Django's own tiny inline helper scripts are allowed; ours must not exist.
    inline_blocks = re.findall(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", content, re.DOTALL)
    for block in inline_blocks:
        assert "Tagify" not in block
        assert "ps-tagify" not in block
