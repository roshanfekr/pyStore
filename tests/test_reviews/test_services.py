import pytest
from django.utils import timezone

from apps.orders.models import Order, OrderItem
from apps.reviews.models import ProductReview
from apps.reviews.services import (
    approve_review,
    create_review,
    has_verified_purchase,
    product_rating,
    product_ratings,
    product_reviews,
    reject_review,
    user_reviews,
)
from core.exceptions import ConflictError, PermissionDeniedError, ValidationError

pytestmark = [pytest.mark.django_db]

CONTENT = "This product is great, I like it a lot."


def test_create_review_defaults_to_pending(product, user):
    review = create_review(product, user, rating=5, title="Great", content=CONTENT)
    assert review.status == ProductReview.STATUS_PENDING
    assert review.is_verified_purchase is False
    assert review.rating == 5


def test_create_review_validates_rating(product, user):
    with pytest.raises(ValidationError):
        create_review(product, user, rating=6, title="T", content=CONTENT)
    with pytest.raises(ValidationError):
        create_review(product, user, rating=0, title="T", content=CONTENT)


def test_create_review_requires_title_and_content_length(product, user):
    with pytest.raises(ValidationError):
        create_review(product, user, rating=4, title="  ", content=CONTENT)
    with pytest.raises(ValidationError):
        create_review(product, user, rating=4, title="T", content="short")


def test_create_review_requires_login(product, db):
    from django.contrib.auth.models import AnonymousUser

    from core.exceptions import AuthenticationFailedError

    with pytest.raises(AuthenticationFailedError):
        create_review(product, AnonymousUser(), rating=4, title="T", content=CONTENT)


def test_create_review_one_per_product(product, user):
    create_review(product, user, rating=5, title="Great", content=CONTENT)
    with pytest.raises(ConflictError):
        create_review(product, user, rating=4, title="Again", content="Different content here.")


def test_create_review_rate_limited(product, user):
    from apps.catalog.services import create_product
    from apps.stores.services import create_store

    store = create_store("Rate Store")
    for index in range(5):
        other = create_product(store, f"Rate Product {index}", price=1)
        create_review(other, user, rating=4, title="Ok", content=f"Review number {index} content.")

    with pytest.raises(ConflictError, match="rate_limited|Too many"):
        create_review(product, user, rating=4, title="Sixth", content="Another review content.")


def test_create_review_rejects_link_spam(product, user):
    spam = "Check http://a.com http://b.com http://c.com http://d.com for deals"
    with pytest.raises(ValidationError, match="links"):
        create_review(product, user, rating=4, title="Spam", content=spam)


def test_create_review_rejects_duplicate_content(product, user):
    create_review(product, user, rating=5, title="Great", content=CONTENT)
    from apps.catalog.services import create_product
    from apps.stores.services import create_store

    other = create_product(create_store("Dup Store"), "Dup Product", price=1)
    with pytest.raises(ConflictError, match="already submitted"):
        create_review(other, user, rating=5, title="Copy", content=CONTENT)


def test_verified_purchase_detection(product, user, store, db):
    assert has_verified_purchase(user, product) is False

    order = Order.objects.create(
        store=store, user=user, email=user.email, payment_status=Order.PAYMENT_PAID
    )
    OrderItem.objects.create(
        order=order, product=product, product_name=product.name,
        quantity=1, unit_price=1, line_total=1,
    )
    assert has_verified_purchase(user, product) is True

    review = create_review(product, user, rating=5, title="Great", content=CONTENT)
    assert review.is_verified_purchase is True


def test_auto_approve_setting(product, user, db):
    from core.settings.service import settings_service

    settings_service.set("reviews", "auto_approve", True)
    review = create_review(product, user, rating=5, title="Great", content=CONTENT)
    assert review.status == ProductReview.STATUS_APPROVED


def test_moderation_transitions(product, user, moderator):
    review = create_review(product, user, rating=4, title="Nice", content=CONTENT)

    approved = approve_review(review, actor=moderator)
    assert approved.status == ProductReview.STATUS_APPROVED
    assert approved.moderated_by == moderator
    assert approved.moderated_at is not None

    with pytest.raises(ConflictError):
        approve_review(approved, actor=moderator)
    with pytest.raises(ConflictError):
        reject_review(approved, actor=moderator, reason="late")


def test_reject_review_records_reason(product, user, moderator):
    review = create_review(product, user, rating=1, title="Bad", content=CONTENT)
    rejected = reject_review(review, actor=moderator, reason="Spam content")
    assert rejected.status == ProductReview.STATUS_REJECTED
    assert rejected.rejection_reason == "Spam content"


def test_moderation_requires_permission(product, user):
    review = create_review(product, user, rating=4, title="Nice", content=CONTENT)
    with pytest.raises(PermissionDeniedError):
        approve_review(review, actor=user)


def test_public_reviews_are_approved_only(product, user, moderator):
    approved = create_review(product, user, rating=5, title="Great", content=CONTENT)
    approve_review(approved, actor=moderator)
    create_review(
        product, moderator, rating=1, title="Meh", content="Not that great honestly."
    )

    public = list(product_reviews(product))
    assert len(public) == 1
    assert public[0].status == ProductReview.STATUS_APPROVED

    history = list(user_reviews(user))
    assert len(history) == 1


def test_product_rating_aggregation(product, user, moderator):
    from apps.catalog.services import create_product
    from apps.stores.services import create_store

    first = create_review(product, user, rating=5, title="Great", content=CONTENT)
    approve_review(first, actor=moderator)

    second_user = None
    from django.contrib.auth import get_user_model

    User = get_user_model()
    second_user = User.objects.create_user(email="second@example.com", password="Str0ng!Passw0rd")
    pending = create_review(product, second_user, rating=1, title="Meh", content=CONTENT)

    summary = product_rating(product)
    assert summary == {"average": 5.0, "count": 1}

    approve_review(pending, actor=moderator)
    summary = product_rating(product)
    assert summary["count"] == 2
    assert summary["average"] == 3.0

    other = create_product(create_store("Agg Store"), "Other Product", price=1)
    assert product_ratings([product.id, other.id])[str(product.id)]["count"] == 2


def test_pending_reviews_older_than_day_are_not_rate_limited(product, user, db):
    from datetime import timedelta

    from apps.catalog.services import create_product
    from apps.stores.services import create_store

    store = create_store("Old Store")
    for index in range(5):
        other = create_product(store, f"Old Product {index}", price=1)
        review = create_review(other, user, rating=4, title="Ok", content=f"Review {index} content.")
        ProductReview.objects.filter(pk=review.pk).update(
            created_at=timezone.now() - timedelta(days=2)
        )

    review = create_review(product, user, rating=4, title="Sixth", content="Another review content.")
    assert review.pk is not None
