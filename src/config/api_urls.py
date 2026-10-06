from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.cart.api import (
    CartCouponView,
    CartItemDetailView,
    CartItemsView,
    CartView,
)
from apps.catalog.api import BrandViewSet, CategoryViewSet, ProductViewSet
from apps.checkout.api import CheckoutMethodsView, CheckoutView
from apps.identity.api import (
    LoginView,
    LogoutView,
    MeUpdateView,
    MeView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    RegisterView,
    VerifyEmailView,
)
from apps.notifications.api import (
    WebhookDeliveryLogViewSet,
    WebhookEndpointViewSet,
)
from apps.orders.api import OrderViewSet
from apps.payments.api import InitializePaymentView
from apps.reviews.api import ReviewViewSet
from apps.shipping.api import (
    RatesView,
    ShippingMethodsView,
    TrackingView,
)

router = DefaultRouter(trailing_slash=False)
router.register("products", ProductViewSet, basename="products")
router.register("categories", CategoryViewSet, basename="categories")
router.register("brands", BrandViewSet, basename="brands")
router.register("orders", OrderViewSet, basename="orders")
router.register("reviews", ReviewViewSet, basename="reviews")
router.register("webhooks/endpoints", WebhookEndpointViewSet, basename="webhook-endpoints")
router.register(
    "webhooks/delivery-logs", WebhookDeliveryLogViewSet, basename="webhook-delivery-logs"
)

urlpatterns = [
    # Authentication
    path("auth/register", RegisterView.as_view(), name="api-register"),
    path("auth/login", LoginView.as_view(), name="api-login"),
    path("auth/logout", LogoutView.as_view(), name="api-logout"),
    path("auth/password-reset", PasswordResetRequestView.as_view(), name="api-password-reset"),
    path(
        "auth/password-reset/confirm",
        PasswordResetConfirmView.as_view(),
        name="api-password-reset-confirm",
    ),
    path("auth/verify-email", VerifyEmailView.as_view(), name="api-verify-email"),
    # Customers
    path("customers/me", MeView.as_view(), name="api-me"),
    path("customers/me/update", MeUpdateView.as_view(), name="api-me-update"),
    # Cart
    path("cart", CartView.as_view(), name="api-cart"),
    path("cart/items", CartItemsView.as_view(), name="api-cart-items"),
    path("cart/items/<str:item_id>", CartItemDetailView.as_view(), name="api-cart-item"),
    path("cart/coupon", CartCouponView.as_view(), name="api-cart-coupon"),
    # Checkout
    path("checkout/methods", CheckoutMethodsView.as_view(), name="api-checkout-methods"),
    path("checkout", CheckoutView.as_view(), name="api-checkout"),
    # Payments
    path(
        "payments/initialize",
        InitializePaymentView.as_view(),
        name="api-payments-initialize",
    ),
    # Shipping
    path("shipping/methods", ShippingMethodsView.as_view(), name="api-shipping-methods"),
    path("shipping/rates", RatesView.as_view(), name="api-shipping-rates"),
    path("shipping/track", TrackingView.as_view(), name="api-shipping-track"),
] + router.urls
