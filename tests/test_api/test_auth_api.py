import pytest
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from apps.identity.models import Customer, User

pytestmark = [pytest.mark.django_db]
PASSWORD = "Str0ng!Passw0rd"


def test_register_creates_user_and_customer(api_client):
    response = api_client.post(
        "/api/v1/auth/register",
        {"email": "new@example.com", "password": PASSWORD, "first_name": "Ali"},
    )
    assert response.status_code == 201
    assert response.data["email"] == "new@example.com"
    user = User.objects.get(email="new@example.com")
    assert Customer.objects.filter(user=user).exists()


def test_register_rejects_duplicate_email(api_client, db):
    User.objects.create_user(email="dup@example.com", password=PASSWORD)
    response = api_client.post(
        "/api/v1/auth/register", {"email": "dup@example.com", "password": PASSWORD}
    )
    assert response.status_code == 409
    assert response.data["error"]["code"] == "identity.email_taken"


def test_register_validates_password(api_client, db):
    response = api_client.post(
        "/api/v1/auth/register", {"email": "weak@example.com", "password": "123"}
    )
    assert response.status_code == 400


def test_login_returns_token(api_client, db):
    User.objects.create_user(email="login@example.com", password=PASSWORD)
    response = api_client.post(
        "/api/v1/auth/login", {"email": "login@example.com", "password": PASSWORD}
    )
    assert response.status_code == 200
    assert Token.objects.filter(user__email="login@example.com").exists()


def test_login_rejects_bad_credentials(api_client, db):
    User.objects.create_user(email="bad@example.com", password=PASSWORD)
    response = api_client.post(
        "/api/v1/auth/login", {"email": "bad@example.com", "password": "Wrong!Pass1"}
    )
    assert response.status_code == 401


def test_logout_revokes_token(api_client, db):
    user = User.objects.create_user(email="out@example.com", password=PASSWORD)
    token, _ = Token.objects.get_or_create(user=user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    assert client.post("/api/v1/auth/logout").status_code == 204
    assert Token.objects.filter(user=user).exists() is False


def test_me_returns_customer_profile(api_client, db):
    user = User.objects.create_user(email="me@example.com", password=PASSWORD)
    Customer.objects.create(user=user, phone="+989121234567")
    token, _ = Token.objects.get_or_create(user=user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    response = client.get("/api/v1/customers/me")
    assert response.status_code == 200
    assert response.data["email"] == "me@example.com"
    assert response.data["phone"] == "+989121234567"


def test_me_requires_authentication(api_client, db):
    assert api_client.get("/api/v1/customers/me").status_code == 401


def test_me_update_changes_names(api_client, db):
    user = User.objects.create_user(email="upd@example.com", password=PASSWORD)
    Customer.objects.create(user=user)
    token, _ = Token.objects.get_or_create(user=user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    response = client.patch(
        "/api/v1/customers/me/update",
        {"first_name": "Updated", "phone": "+989122222222"},
    )
    assert response.status_code == 200
    user.refresh_from_db()
    assert user.first_name == "Updated"


def test_password_reset_flow(api_client, db):
    from apps.identity.models import PasswordResetToken

    user = User.objects.create_user(email="reset@example.com", password=PASSWORD)
    api_client.post("/api/v1/auth/password-reset", {"email": "reset@example.com"})
    token = PasswordResetToken.objects.get(user=user)

    response = api_client.post(
        "/api/v1/auth/password-reset/confirm",
        {"token": str(token.token), "password": "New!Passw0rd1"},
    )
    assert response.status_code == 200
    user.refresh_from_db()
    assert user.check_password("New!Passw0rd1")


def test_verify_email_flow(api_client, db):
    from apps.identity.services.verification import issue_email_verification

    user = User.objects.create_user(email="verify@example.com", password=PASSWORD)
    verification = issue_email_verification(user)
    response = api_client.post(
        "/api/v1/auth/verify-email", {"token": str(verification.token)}
    )
    assert response.status_code == 200
    user.refresh_from_db()
    assert user.email_verified is True


def test_unsupported_version_returns_404(api_client, db):
    response = api_client.get("/api/v9/products")
    assert response.status_code == 404
