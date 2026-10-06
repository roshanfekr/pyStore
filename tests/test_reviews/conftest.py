import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.catalog.services import create_product, publish_product
from apps.identity.services.roles import ensure_permission, ensure_role, grant_role
from apps.orders.models import Order, OrderItem
from apps.reviews.models import ProductReview
from apps.stores.services import create_store

User = get_user_model()

PASSWORD = "Str0ng!Passw0rd"


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def store(db):
    return create_store("Reviews Store")


@pytest.fixture
def product(db, store):
    product = create_product(store, "Review Product", price=1)
    publish_product(product)
    return product


@pytest.fixture
def user(db):
    return User.objects.create_user(email="reviewer@example.com", password=PASSWORD)


@pytest.fixture
def moderator(db):
    user = User.objects.create_user(
        email="moderator@example.com", password=PASSWORD, is_staff=True
    )
    permission, _ = ensure_permission("reviews.review.moderate", display_name="Moderate reviews")
    role = ensure_role("Review Moderators")
    role.permissions.add(permission)
    grant_role(user, role.name)
    return user


@pytest.fixture
def auth_client(api_client, user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def moderator_client(api_client, moderator):
    client = APIClient()
    client.force_authenticate(user=moderator)
    return client


@pytest.fixture
def paid_order(db, user, store, product):
    order = Order.objects.create(
        store=store, user=user, email=user.email, payment_status=Order.PAYMENT_PAID
    )
    OrderItem.objects.create(
        order=order, product=product, product_name=product.name,
        quantity=1, unit_price=product.price, line_total=product.price,
    )
    return order


def make_review(db, product, user, **overrides):
    defaults = {
        "rating": 5,
        "title": "Great",
        "content": "This product is great, I like it a lot.",
        "status": ProductReview.STATUS_APPROVED,
    }
    defaults.update(overrides)
    return ProductReview.objects.create(product=product, user=user, **defaults)
