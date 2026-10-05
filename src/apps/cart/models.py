from django.conf import settings
from django.db import models

from core.models import BaseModel


class Cart(BaseModel):
    STATUS_ACTIVE = "active"
    STATUS_ORDERED = "ordered"
    STATUS_ABANDONED = "abandoned"
    STATUS_CHOICES = [
        (STATUS_ACTIVE, "Active"),
        (STATUS_ORDERED, "Ordered"),
        (STATUS_ABANDONED, "Abandoned"),
    ]

    store = models.ForeignKey("stores.Store", related_name="carts", on_delete=models.PROTECT)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, related_name="carts", on_delete=models.CASCADE
    )
    session_key = models.CharField(max_length=64, null=True, blank=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    coupon = models.ForeignKey(
        "pricing.Discount", null=True, blank=True, related_name="carts", on_delete=models.SET_NULL
    )

    class Meta:
        verbose_name = "Cart"
        verbose_name_plural = "Carts"
        constraints = [
            models.UniqueConstraint(
                fields=["store", "user"],
                condition=models.Q(user__isnull=False, status="active"),
                name="uniq_active_cart_user",
            ),
            models.UniqueConstraint(
                fields=["store", "session_key"],
                condition=models.Q(user__isnull=True, session_key__isnull=False, status="active"),
                name="uniq_active_cart_session",
            ),
        ]

    def __str__(self):
        owner = self.user.email if self.user_id else self.session_key
        return f"Cart {self.store_id}:{owner}"


class CartItem(BaseModel):
    cart = models.ForeignKey(Cart, related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey("catalog.Product", related_name="cart_items", on_delete=models.CASCADE)
    variant = models.ForeignKey(
        "catalog.ProductVariant", null=True, blank=True, related_name="cart_items", on_delete=models.CASCADE
    )
    quantity = models.PositiveIntegerField(default=1)
    unit_price_at_add = models.DecimalField(max_digits=18, decimal_places=4)

    class Meta:
        verbose_name = "Cart item"
        verbose_name_plural = "Cart items"
        constraints = [
            models.UniqueConstraint(
                fields=["cart", "product", "variant"], name="uniq_cart_item"
            ),
        ]

    def __str__(self):
        return f"{self.product_id} x{self.quantity}"


class WishlistItem(BaseModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name="wishlist_items", on_delete=models.CASCADE
    )
    product = models.ForeignKey("catalog.Product", related_name="wishlist_items", on_delete=models.CASCADE)

    class Meta:
        verbose_name = "Wishlist item"
        verbose_name_plural = "Wishlist items"
        constraints = [
            models.UniqueConstraint(fields=["user", "product"], name="uniq_wishlist_item"),
        ]


class CompareItem(BaseModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, related_name="compare_items", on_delete=models.CASCADE
    )
    session_key = models.CharField(max_length=64, null=True, blank=True)
    product = models.ForeignKey("catalog.Product", related_name="compare_items", on_delete=models.CASCADE)

    class Meta:
        verbose_name = "Compare item"
        verbose_name_plural = "Compare items"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "product"],
                condition=models.Q(user__isnull=False),
                name="uniq_compare_user_product",
            ),
            models.UniqueConstraint(
                fields=["session_key", "product"],
                condition=models.Q(session_key__isnull=False),
                name="uniq_compare_session_product",
            ),
        ]
