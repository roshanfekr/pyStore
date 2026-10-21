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
    AddressDetailView,
    AddressListCreateView,
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
from apps.storefront.api import (
    BlogDetailView,
    BlogListView,
    BootstrapView,
    CompareDetailView,
    CompareView,
    HookView,
    PageDetailView,
    SearchView,
    WishlistDetailView,
    WishlistMoveView,
    WishlistView,
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
    path(
        "customers/me/addresses",
        AddressListCreateView.as_view(),
        name="api-me-addresses",
    ),
    path(
        "customers/me/addresses/<int:address_id>",
        AddressDetailView.as_view(),
        name="api-me-address",
    ),
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
    # Storefront SPA
    path("storefront/bootstrap", BootstrapView.as_view(), name="api-storefront-bootstrap"),
    path("storefront/hooks/<str:hook_name>", HookView.as_view(), name="api-storefront-hook"),
    path("storefront/search", SearchView.as_view(), name="api-storefront-search"),
    path("storefront/pages/<slug:slug>", PageDetailView.as_view(), name="api-storefront-page"),
    path("storefront/blog", BlogListView.as_view(), name="api-storefront-blog"),
    path("storefront/blog/<slug:slug>", BlogDetailView.as_view(), name="api-storefront-blog-detail"),
    path("storefront/wishlist", WishlistView.as_view(), name="api-storefront-wishlist"),
    path("storefront/wishlist/move", WishlistMoveView.as_view(), name="api-storefront-wishlist-move"),
    path(
        "storefront/wishlist/<int:product_id>",
        WishlistDetailView.as_view(),
        name="api-storefront-wishlist-detail",
    ),
    path("storefront/compare", CompareView.as_view(), name="api-storefront-compare"),
    path(
        "storefront/compare/<int:product_id>",
        CompareDetailView.as_view(),
        name="api-storefront-compare-detail",
    ),
] + router.urls
