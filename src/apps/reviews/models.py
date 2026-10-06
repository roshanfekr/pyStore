from django.conf import settings
from django.db import models

from core.models import BaseModel


class ProductReview(BaseModel):
    STATUS_PENDING = "pending"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_REJECTED, "Rejected"),
    ]

    product = models.ForeignKey(
        "catalog.Product", related_name="reviews", on_delete=models.CASCADE
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name="product_reviews", on_delete=models.CASCADE
    )
    rating = models.PositiveSmallIntegerField()
    title = models.CharField(max_length=255)
    content = models.TextField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True)
    is_verified_purchase = models.BooleanField(default=False)
    moderated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        related_name="moderated_reviews",
        on_delete=models.SET_NULL,
    )
    moderated_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.CharField(max_length=255, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        verbose_name = "Product review"
        verbose_name_plural = "Product reviews"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["product", "user"],
                condition=models.Q(is_deleted=False),
                name="uniq_active_review_per_product_user",
            )
        ]

    def __str__(self):
        return f"{self.product_id} - {self.rating}/5 by {self.user_id}"
