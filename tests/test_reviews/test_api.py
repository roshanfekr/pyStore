import pytest

from apps.reviews.models import ProductReview

pytestmark = [pytest.mark.django_db]

CONTENT = "This product is great, I like it a lot."


def create(product, user, **kwargs):
    from apps.reviews.services import create_review

    return create_review(product, user, rating=kwargs.pop("rating", 5),
                         title=kwargs.pop("title", "Great"), content=kwargs.pop("content", CONTENT),
                         **kwargs)


def test_anonymous_sees_only_approved(api_client, product, user, moderator, db):
    review = create(product, user)
    approve_action(review, moderator)

    response = api_client.get("/api/v1/reviews", {"product": product.slug})
    assert response.status_code == 200
    assert response.data["count"] == 1
    assert response.data["results"][0]["status"] == "approved"


def approve_action(review, moderator):
    from apps.reviews.services import approve_review

    return approve_review(review, actor=moderator)


def test_reviews_require_authentication(api_client, product, db):
    response = api_client.post(
        "/api/v1/reviews",
        {"product": product.slug, "rating": 5, "title": "Great", "content": CONTENT},
        format="json",
    )
    assert response.status_code == 401


def test_create_review_via_api(auth_client, product, user, db):
    response = auth_client.post(
        "/api/v1/reviews",
        {"product": product.slug, "rating": 4, "title": "Nice", "content": CONTENT},
        format="json",
    )
    assert response.status_code == 201, response.data
    assert response.data["status"] == "pending"
    assert response.data["is_verified_purchase"] is False
    assert ProductReview.objects.filter(product=product, user=user).exists()


def test_create_review_domain_error_format(auth_client, product, user, db):
    create(product, user)
    response = auth_client.post(
        "/api/v1/reviews",
        {"product": product.slug, "rating": 4, "title": "Again", "content": "Different content here."},
        format="json",
    )
    assert response.status_code == 409
    assert response.data["error"]["code"] == "reviews.already_reviewed"


def test_mine_returns_customer_history(auth_client, product, user, db):
    create(product, user)
    response = auth_client.get("/api/v1/reviews/mine")
    assert response.status_code == 200
    assert response.data["count"] == 1
    assert response.data["results"][0]["status"] == "pending"


def test_mine_requires_authentication(api_client, db):
    assert api_client.get("/api/v1/reviews/mine").status_code == 401


def test_summary_endpoint(api_client, product, user, moderator, db):
    review = create(product, user)
    approve_action(review, moderator)
    response = api_client.get("/api/v1/reviews/summary", {"product": product.slug})
    assert response.status_code == 200
    assert response.data == {"average": 5.0, "count": 1}


def test_moderation_endpoints_require_permission(auth_client, product, user, db):
    review = create(product, user)
    assert auth_client.post(f"/api/v1/reviews/{review.id}/approve").status_code == 403
    assert (
        auth_client.post(f"/api/v1/reviews/{review.id}/reject", {"reason": "x"}, format="json").status_code
        == 403
    )


def test_moderator_can_approve_and_reject(moderator_client, moderator, product, user, db):
    review = create(product, user)
    response = moderator_client.post(f"/api/v1/reviews/{review.id}/approve")
    assert response.status_code == 200
    assert response.data["status"] == "approved"

    second = create(product, moderator, title="Second", content="Second review body here.")
    response = moderator_client.post(
        f"/api/v1/reviews/{second.id}/reject", {"reason": "Off-topic"}, format="json"
    )
    assert response.status_code == 200
    assert response.data["status"] == "rejected"
    assert response.data["rejection_reason"] == "Off-topic"


def test_retrieve_visibility_rules(api_client, auth_client, moderator_client, product, user, moderator, db):
    review = create(product, user)

    assert api_client.get(f"/api/v1/reviews/{review.id}").status_code == 404
    assert auth_client.get(f"/api/v1/reviews/{review.id}").status_code == 200
    assert moderator_client.get(f"/api/v1/reviews/{review.id}").status_code == 200

    approve_action(review, moderator)
    assert api_client.get(f"/api/v1/reviews/{review.id}").status_code == 200


def test_reviews_filter_and_sort(api_client, product, user, moderator, db):
    from django.contrib.auth import get_user_model

    User = get_user_model()
    other = User.objects.create_user(email="other@example.com", password="Str0ng!Passw0rd")
    first = create(product, user, rating=3, title="Three", content="Rated three stars overall.")
    second = create(product, other, rating=5, title="Five", content="Rated five stars overall.")
    approve_action(first, moderator)
    approve_action(second, moderator)

    response = api_client.get("/api/v1/reviews", {"product": product.slug, "rating": "5"})
    assert response.data["count"] == 1
    assert response.data["results"][0]["rating"] == 5

    response = api_client.get("/api/v1/reviews", {"product": product.slug, "ordering": "rating"})
    assert response.data["results"][0]["rating"] == 3

    response = api_client.get("/api/v1/reviews", {"search": "five stars"})
    assert response.data["count"] == 1
