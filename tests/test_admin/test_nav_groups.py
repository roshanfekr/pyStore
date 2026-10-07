import pytest
from django.contrib.auth import get_user_model

User = get_user_model()

pytestmark = [pytest.mark.django_db]


@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser(email="nav-admin@example.com", password="Str0ng!Passw0rd")


def test_sidebar_groups_are_collapsible(client, admin_user):
    client.force_login(admin_user)
    content = client.get("/admin/").content.decode()

    assert 'class="psnav-table psnav-collapsible" id="psnav-group-overview"' in content
    assert 'id="psnav-group-plugin-settings"' not in content  # no enabled plugins with pages yet
    assert "psnav-caret" in content
    assert 'aria-expanded="true"' in content
    assert 'id="psnav-group-app-' in content


def test_sidebar_group_state_persists_via_script(client, admin_user):
    client.force_login(admin_user)
    content = client.get("/admin/").content.decode()
    assert 'src="/static/admin_panel/js/nav_groups.js"' in content
