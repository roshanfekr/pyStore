import pytest

from apps.reviews.models import ProductReview

pytestmark = [pytest.mark.django_db]


def test_review_defaults_and_str(product, user):
    review = ProductReview.objects.create(
        product=product, user=user, rating=4, title="Ok", content="Fine overall quality."
    )
    assert review.status == ProductReview.STATUS_PENDING
    assert review.is_verified_purchase is False
    assert "4/5" in str(review)


def test_active_review_unique_per_product_user(product, user):
    from django.db.utils import IntegrityError

    ProductReview.objects.create(
        product=product, user=user, rating=3, title="One", content="First review content."
    )
    with pytest.raises(IntegrityError):
        ProductReview.objects.create(
            product=product, user=user, rating=3, title="Two", content="Second review content."
        )


def test_soft_deleted_review_allows_new_one(product, user):
    first = ProductReview.objects.create(
        product=product, user=user, rating=3, title="One", content="First review content."
    )
    first.delete()

    second = ProductReview.objects.create(
        product=product, user=user, rating=4, title="Two", content="Second review content."
    )
    assert second.status == ProductReview.STATUS_PENDING
    assert ProductReview.objects.filter(product=product, user=user).count() == 1
