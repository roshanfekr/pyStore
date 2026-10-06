import re

from django.db.models import Avg, Count, Q
from django.utils import timezone

from apps.identity.models import User
from apps.orders.models import Order, OrderItem
from apps.reviews.events import ReviewModerated, ReviewSubmitted
from apps.reviews.models import ProductReview
from core.events import dispatcher
from core.exceptions import (
    AuthenticationFailedError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
)
from core.settings.service import settings_service

NAMESPACE = "reviews"

URL_PATTERN = re.compile(r"https?://", re.IGNORECASE)


def register_review_settings() -> None:
    settings_service.register(NAMESPACE, "auto_approve", default=False, value_type=bool)
    settings_service.register(NAMESPACE, "max_per_day", default=5, value_type=int)
    settings_service.register(NAMESPACE, "max_links", default=3, value_type=int)
    settings_service.register(NAMESPACE, "content_min_length", default=10, value_type=int)
    settings_service.register(NAMESPACE, "content_max_length", default=5000, value_type=int)


def _setting(key: str) -> int:
    try:
        return int(settings_service.get(NAMESPACE, key))
    except (TypeError, ValueError):
        return 0


def has_verified_purchase(user, product) -> bool:
    """A purchase counts as verified once the order is paid (or beyond)."""
    return OrderItem.objects.filter(
        order__user=user,
        product=product,
    ).filter(
        Q(order__payment_status=Order.PAYMENT_PAID)
        | Q(order__status__in=[Order.STATUS_PAID, Order.STATUS_SHIPPED, Order.STATUS_COMPLETED])
    ).exists()


def _validate_rating(rating) -> int:
    try:
        rating = int(rating)
    except (TypeError, ValueError):
        raise ValidationError("Rating must be a number", code="reviews.bad_rating") from None
    if rating < 1 or rating > 5:
        raise ValidationError("Rating must be between 1 and 5", code="reviews.bad_rating")
    return rating


def _validate_text(title: str, content: str) -> tuple[str, str]:
    title = (title or "").strip()
    content = (content or "").strip()
    if not title:
        raise ValidationError("Review title is required", code="reviews.title_required")
    min_length = _setting("content_min_length") or 10
    max_length = _setting("content_max_length") or 5000
    if len(content) < min_length:
        raise ValidationError(
            f"Review content must be at least {min_length} characters",
            code="reviews.content_too_short",
        )
    if len(content) > max_length:
        raise ValidationError(
            f"Review content must be at most {max_length} characters",
            code="reviews.content_too_long",
        )
    return title, content


def _check_rate_limit(user) -> None:
    from datetime import timedelta

    from django.utils import timezone as tz

    max_per_day = _setting("max_per_day") or 5
    window_start = tz.now() - timedelta(hours=24)
    recent = ProductReview.objects.filter(user=user, created_at__gte=window_start).count()
    if recent >= max_per_day:
        raise ConflictError(
            f"Too many reviews submitted today (limit {max_per_day})",
            code="reviews.rate_limited",
        )


def _check_spam_content(content: str) -> None:
    max_links = _setting("max_links") or 3
    if len(URL_PATTERN.findall(content)) > max_links:
        raise ValidationError(
            "Review contains too many links", code="reviews.spam_links"
        )


def _check_duplicate_content(user, content: str) -> None:
    if ProductReview.objects.filter(user=user, content__iexact=content).exists():
        raise ConflictError(
            "This review content was already submitted", code="reviews.duplicate_content"
        )


def create_review(product, user, *, rating, title, content, ip_address=None) -> ProductReview:
    if user is None or not getattr(user, "is_authenticated", False):
        raise AuthenticationFailedError(
            "Login is required to review", code="reviews.login_required"
        )

    rating = _validate_rating(rating)
    title, content = _validate_text(title, content)
    _check_rate_limit(user)
    _check_spam_content(content)
    _check_duplicate_content(user, content)

    if ProductReview.objects.filter(product=product, user=user).exists():
        raise ConflictError(
            "You have already reviewed this product", code="reviews.already_reviewed"
        )

    auto_approve = bool(settings_service.get(NAMESPACE, "auto_approve"))
    review = ProductReview.objects.create(
        product=product,
        user=user,
        rating=rating,
        title=title,
        content=content,
        status=ProductReview.STATUS_APPROVED if auto_approve else ProductReview.STATUS_PENDING,
        is_verified_purchase=has_verified_purchase(user, product),
        ip_address=ip_address,
    )
    dispatcher.dispatch_async(
        ReviewSubmitted(
            review_id=str(review.id),
            product_id=str(product.id),
            user_id=str(user.id),
            rating=review.rating,
            is_verified_purchase=review.is_verified_purchase,
        )
    )
    return review


def _moderator(actor) -> User:
    if actor is None or not getattr(actor, "is_authenticated", False):
        raise PermissionDeniedError("Login required", code="reviews.login_required")
    if not actor.has_perm("reviews.review.moderate"):
        raise PermissionDeniedError(
            "Moderation permission required", code="reviews.moderation_required"
        )
    return actor


def approve_review(review: ProductReview, *, actor, request=None) -> ProductReview:
    moderator = _moderator(actor)
    if review.status != ProductReview.STATUS_PENDING:
        raise ConflictError(
            "Only pending reviews can be approved", code="reviews.invalid_transition"
        )
    review.status = ProductReview.STATUS_APPROVED
    review.moderated_by = moderator
    review.moderated_at = timezone.now()
    review.rejection_reason = ""
    review.save(update_fields=["status", "moderated_by", "moderated_at", "rejection_reason"])
    _audit_moderation("review.approved", review, moderator, request)
    _dispatch_moderated(review, moderator)
    return review


def reject_review(review: ProductReview, *, actor, reason: str = "", request=None) -> ProductReview:
    moderator = _moderator(actor)
    if review.status != ProductReview.STATUS_PENDING:
        raise ConflictError(
            "Only pending reviews can be rejected", code="reviews.invalid_transition"
        )
    review.status = ProductReview.STATUS_REJECTED
    review.moderated_by = moderator
    review.moderated_at = timezone.now()
    review.rejection_reason = (reason or "").strip()[:255]
    review.save(update_fields=["status", "moderated_by", "moderated_at", "rejection_reason"])
    _audit_moderation("review.rejected", review, moderator, request)
    _dispatch_moderated(review, moderator)
    return review


def _audit_moderation(action: str, review: ProductReview, moderator, request) -> None:
    from core.audit.service import audit

    audit(
        action,
        "product_review",
        str(review.id),
        actor=moderator,
        request=request,
        before={"status": ProductReview.STATUS_PENDING},
        after={"status": review.status, "reason": review.rejection_reason},
    )


def _dispatch_moderated(review: ProductReview, moderator) -> None:
    dispatcher.dispatch_async(
        ReviewModerated(
            review_id=str(review.id),
            product_id=str(review.product_id),
            status=review.status,
            moderator_id=str(moderator.id),
        )
    )


def product_reviews(product):
    """Public review list: approved reviews only."""
    return product.reviews.filter(status=ProductReview.STATUS_APPROVED)


def user_reviews(user):
    return ProductReview.objects.filter(user=user)


def pending_reviews():
    return ProductReview.objects.filter(status=ProductReview.STATUS_PENDING)


def product_rating(product) -> dict:
    result = product.reviews.filter(status=ProductReview.STATUS_APPROVED).aggregate(
        average=Avg("rating"), count=Count("id")
    )
    average = result["average"]
    return {
        "average": round(float(average), 2) if average is not None else None,
        "count": result["count"] or 0,
    }


def product_ratings(product_ids) -> dict:
    rows = (
        ProductReview.objects.filter(
            product_id__in=product_ids, status=ProductReview.STATUS_APPROVED
        )
        .values("product_id")
        .annotate(average=Avg("rating"), count=Count("id"))
    )
    return {
        str(row["product_id"]): {
            "average": round(float(row["average"]), 2),
            "count": row["count"],
        }
        for row in rows
    }


def get_review(review_id, *, for_user=None) -> ProductReview:
    review = ProductReview.objects.filter(pk=review_id).first()
    if review is None:
        raise NotFoundError("Review not found", code="reviews.not_found")
    public = review.status == ProductReview.STATUS_APPROVED
    own = for_user is not None and review.user_id == for_user.id
    moderator = for_user is not None and for_user.has_perm("reviews.review.moderate")
    if not (public or own or moderator):
        raise NotFoundError("Review not found", code="reviews.not_found")
    return review
