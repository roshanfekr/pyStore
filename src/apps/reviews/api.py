from rest_framework import mixins, serializers
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from apps.catalog.models import Product
from apps.identity.api import has_perm
from apps.reviews.models import ProductReview
from apps.reviews.services import (
    approve_review,
    create_review,
    get_review,
    product_rating,
    reject_review,
    user_reviews,
)
from core.api.filters import QueryParamFilterMixin
from core.exceptions import NotFoundError


class ReviewSerializer(serializers.ModelSerializer):
    product = serializers.SlugRelatedField(slug_field="slug", read_only=True)
    user = serializers.SlugRelatedField(slug_field="email", read_only=True)

    class Meta:
        model = ProductReview
        fields = [
            "id", "product", "user", "rating", "title", "content", "status",
            "is_verified_purchase", "rejection_reason", "created_at",
        ]
        read_only_fields = ["status", "is_verified_purchase", "rejection_reason"]


class CreateReviewSerializer(serializers.Serializer):
    product = serializers.CharField()
    rating = serializers.IntegerField(min_value=1, max_value=5)
    title = serializers.CharField(max_length=255)
    content = serializers.CharField()


class RejectReviewSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, default="")


def _resolve_product(slug: str) -> Product:
    try:
        return Product.objects.get(slug=slug)
    except (Product.DoesNotExist, ValueError, TypeError):
        raise NotFoundError("Product not found", code="reviews.product_not_found") from None


class ReviewViewSet(
    QueryParamFilterMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, GenericViewSet
):
    """Public product reviews plus customer history and admin moderation."""

    serializer_class = ReviewSerializer
    permission_classes = [AllowAny]

    query_filters = {
        "product": "product__slug",
        "rating": "rating",
        "status": "status",
    }
    ordering_fields = ("created_at", "rating")
    search_fields = ("title", "content")
    default_ordering = "-created_at"

    def get_queryset(self):
        queryset = ProductReview.objects.select_related("product", "user")
        user = self.request.user
        if user.is_authenticated and user.has_perm("reviews.review.moderate"):
            return queryset
        return queryset.filter(status=ProductReview.STATUS_APPROVED)

    def retrieve(self, request, *args, **kwargs):
        review = get_review(self.kwargs.get("pk"), for_user=request.user)
        return Response(ReviewSerializer(review).data)

    def create(self, request, *args, **kwargs):
        serializer = CreateReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        product = _resolve_product(data["product"])
        review = create_review(
            product,
            request.user,
            rating=data["rating"],
            title=data["title"],
            content=data["content"],
            ip_address=request.META.get("REMOTE_ADDR"),
        )
        return Response(ReviewSerializer(review).data, status=201)

    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated])
    def mine(self, request, *args, **kwargs):
        queryset = self.filter_queryset(user_reviews(request.user))
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page if page is not None else queryset, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def summary(self, request, *args, **kwargs):
        slug = request.query_params.get("product")
        if not slug:
            raise NotFoundError("Product is required", code="reviews.product_required")
        product = _resolve_product(slug)
        return Response(product_rating(product))

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated, has_perm("reviews.review.moderate")])
    def approve(self, request, pk=None, *args, **kwargs):
        review = get_review(pk, for_user=request.user)
        review = approve_review(review, actor=request.user)
        return Response(ReviewSerializer(review).data)

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated, has_perm("reviews.review.moderate")])
    def reject(self, request, pk=None, *args, **kwargs):
        review = get_review(pk, for_user=request.user)
        serializer = RejectReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        review = reject_review(
            review, actor=request.user, reason=serializer.validated_data["reason"]
        )
        return Response(ReviewSerializer(review).data)
