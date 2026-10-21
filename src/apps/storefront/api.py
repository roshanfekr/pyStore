"""Storefront JSON API consumed by the Vue SPA.

The SPA is a thin client: it renders the same data the server-rendered themes
use. Theme branding/config and plugin hook fragments are exposed here so the
existing theme and plugin systems keep working after the frontend moved to Vue.
"""

from django.conf import settings
from django.middleware.csrf import get_token
from django.templatetags.static import static as static_url
from rest_framework import serializers
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.cart.compare import add_to_compare, compare_list, remove_from_compare
from apps.cart.models import CompareItem, WishlistItem
from apps.cart.services import available_quantity_for
from apps.cart.wishlist import add_to_wishlist, move_to_cart, remove_from_wishlist, wishlist_for
from apps.catalog.models import Product, ProductImage, ProductVariant
from apps.catalog.services import product_option_groups, resolve_price
from apps.cms.models import BlogPost, Menu, Page, Widget
from apps.storefront.hooks import render_plugin_hook
from apps.storefront.themes import get_active_theme_name, get_theme_config, get_theme_static_dir
from apps.storefront.views import _current_store, format_money
from apps.stores.services import (
    get_active_currencies,
    get_active_currency_code,
    get_active_languages,
    get_currency,
    get_language,
)
from core.exceptions import ApplicationError, NotFoundError


def _static(path: str) -> str:
    """Root-relative URL for a static asset (STATIC_URL may omit the slash)."""
    return "/" + static_url(path).lstrip("/")


def _menu_tree(menu: Menu, parent=None) -> list[dict]:
    items = menu.items.filter(parent=parent).order_by("ordering") if parent is not None else menu.items.filter(
        parent__isnull=True
    ).order_by("ordering")
    return [
        {
            "id": str(item.id),
            "title": item.title,
            "url": item.url,
            "open_in_new_tab": item.open_in_new_tab,
            "children": _menu_tree(menu, item),
        }
        for item in items
    ]


def _theme_css_urls() -> list[str]:
    base = get_theme_static_dir()
    if base is None or not base.exists():
        return []
    return [_static(path.relative_to(base).as_posix()) for path in sorted(base.rglob("*.css"))]


def _storefront_bootstrap(request) -> dict:
    branding = get_theme_config()
    branding.setdefault("site_name", "pyStore")

    menu = Menu.objects.filter(slug="main").first()
    menu_items = _menu_tree(menu) if menu is not None else []
    widgets = [
        {"name": w.name, "slug": w.slug, "widget_type": w.widget_type, "content": w.content}
        for w in Widget.objects.filter(is_active=True).order_by("name")[:5]
    ]

    from django.utils import translation

    active_code = translation.get_language() or "en"
    active_language = get_language(active_code)

    active_currency_code = get_active_currency_code(
        request.COOKIES.get(settings.CURRENCY_COOKIE_NAME)
    )
    active_currency = get_currency(active_currency_code)
    currencies = get_active_currencies()

    user = {"is_authenticated": False}
    wishlist_count = 0
    compare_count = 0
    if request.user.is_authenticated:
        from apps.cart.compare import CompareItem
        from apps.cart.wishlist import WishlistItem

        user = {
            "is_authenticated": True,
            "id": str(request.user.id),
            "email": request.user.email,
            "first_name": request.user.first_name,
            "last_name": request.user.last_name,
            "is_staff": request.user.is_staff,
        }
        wishlist_count = WishlistItem.objects.filter(user=request.user).count()
        compare_count = CompareItem.objects.filter(user=request.user).count()

    return {
        "theme": {"name": get_active_theme_name(), "config": branding, "css": _theme_css_urls()},
        "branding": branding,
        "menu": menu_items,
        "widgets": widgets,
        "languages": [
            {
                "code": language.code,
                "name": language.name,
                "flag": language.flag,
                "direction": language.direction,
                "is_current": language.code == active_code,
            }
            for language in get_active_languages()
        ],
        "active_language": {
            "code": active_code,
            "name": active_language.name if active_language else active_code,
            "direction": active_language.direction if active_language else "ltr",
        },
        "currencies": [
            {
                "code": currency.code,
                "name": currency.name,
                "symbol": currency.symbol,
                "decimal_places": currency.decimal_places,
                "is_current": currency.code == active_currency_code,
            }
            for currency in currencies
        ],
        "active_currency": {
            "code": active_currency_code,
            "name": active_currency.name if active_currency else active_currency_code,
            "symbol": active_currency.symbol if active_currency else "",
        },
        "user": user,
        "counts": {"wishlist": wishlist_count, "compare": compare_count},
        "static_url": settings.STATIC_URL,
        "admin_url": "/admin/",
    }


class StorefrontProductSerializer(serializers.ModelSerializer):
    category = serializers.SlugRelatedField(slug_field="slug", read_only=True)
    brand = serializers.SlugRelatedField(slug_field="slug", read_only=True)

    class Meta:
        model = Product
        fields = [
            "id", "name", "slug", "description", "product_type",
            "category", "brand", "price", "compare_at_price", "stock_quantity",
        ]


def _resolved_price(product: Product, variant: ProductVariant | None = None):
    """Price resolved through the pricing registry (plugin modifiers included).

    ``None`` is returned when no price is configured, so the storefront can
    state that the price is unavailable instead of inventing one.
    """
    try:
        return resolve_price(product, variant)
    except ValueError:
        return None


def _available_quantity(product: Product, variant: ProductVariant | None = None):
    """Available quantity for a product or variant.

    ``None`` means the item is not stock-controlled (digital products).
    """
    return available_quantity_for(product, variant)


def _is_in_stock(available) -> bool:
    return True if available is None else available > 0


class StorefrontProductImageSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()
    alt = serializers.SerializerMethodField()

    class Meta:
        model = ProductImage
        fields = ["id", "url", "alt", "position", "is_main"]

    def get_url(self, obj):
        try:
            return obj.image.url
        except ValueError:
            return ""

    def get_alt(self, obj):
        return obj.alt_text or ""


class StorefrontProductVariantSerializer(serializers.ModelSerializer):
    price = serializers.SerializerMethodField()
    price_value = serializers.SerializerMethodField()
    compare_at_price = serializers.SerializerMethodField()
    in_stock = serializers.SerializerMethodField()
    available_quantity = serializers.SerializerMethodField()
    attributes = serializers.SerializerMethodField()

    class Meta:
        model = ProductVariant
        fields = [
            "id", "sku", "price", "price_value", "compare_at_price",
            "in_stock", "available_quantity", "attributes", "is_default",
        ]

    def _product(self):
        return self.context["product"]

    def _currency(self):
        return self.context.get("currency")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._price_cache = {}
        self._available_cache = {}

    def _price(self, obj):
        if obj.pk not in self._price_cache:
            self._price_cache[obj.pk] = _resolved_price(self._product(), obj)
        return self._price_cache[obj.pk]

    def _available(self, obj):
        if obj.pk not in self._available_cache:
            self._available_cache[obj.pk] = _available_quantity(self._product(), obj)
        return self._available_cache[obj.pk]

    def get_price(self, obj):
        return format_money(self._price(obj), self._currency())

    def get_price_value(self, obj):
        price = self._price(obj)
        return str(price) if price is not None else ""

    def get_compare_at_price(self, obj):
        return format_money(obj.compare_at_price, self._currency())

    def get_in_stock(self, obj):
        return _is_in_stock(self._available(obj))

    def get_available_quantity(self, obj):
        return self._available(obj)

    def get_attributes(self, obj):
        return {
            link.attribute.slug: link.value.value
            for link in obj.attributes.all()
        }


class StorefrontProductDetailSerializer(serializers.ModelSerializer):
    """Product detail payload for the storefront product page.

    The catalog product endpoint exposes the product record only. The product
    page also needs the images, the variant combinations and the availability
    the cart enforces, so they are assembled here from the same models and
    services the server-rendered product page uses.
    """

    category = serializers.SerializerMethodField()
    brand = serializers.SerializerMethodField()
    images = serializers.SerializerMethodField()
    options = serializers.SerializerMethodField()
    variants = serializers.SerializerMethodField()
    selected_variant = serializers.SerializerMethodField()
    price = serializers.SerializerMethodField()
    price_value = serializers.SerializerMethodField()
    compare_at_price = serializers.SerializerMethodField()
    in_stock = serializers.SerializerMethodField()
    available_quantity = serializers.SerializerMethodField()
    currency = serializers.SerializerMethodField()
    meta_title = serializers.SerializerMethodField()
    meta_description = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id", "name", "slug", "description", "product_type", "sku",
            "category", "brand", "images", "options", "variants",
            "selected_variant", "price", "price_value", "compare_at_price",
            "in_stock", "available_quantity", "currency", "meta_title",
            "meta_description",
        ]

    def _currency(self):
        return self.context.get("currency")

    def _active_variants(self):
        return [variant for variant in self.instance.variants.all() if variant.is_active]

    def _selected_variant(self):
        variants = self._active_variants()
        return variants[0] if variants else None

    def get_category(self, obj):
        if obj.category_id is None:
            return None
        return {"slug": obj.category.slug, "name": obj.category.name}

    def get_brand(self, obj):
        if obj.brand_id is None:
            return None
        return {"slug": obj.brand.slug, "name": obj.brand.name}

    def get_images(self, obj):
        return StorefrontProductImageSerializer(obj.images.all(), many=True).data

    def get_options(self, obj):
        return product_option_groups(obj)

    def get_variants(self, obj):
        variants = self._active_variants()
        return StorefrontProductVariantSerializer(
            variants, many=True, context=self.context
        ).data

    def get_selected_variant(self, obj):
        variant = self._selected_variant()
        return variant.sku if variant is not None else ""

    def get_price(self, obj):
        variant = self._selected_variant()
        return format_money(_resolved_price(obj, variant), self._currency())

    def get_price_value(self, obj):
        variant = self._selected_variant()
        price = _resolved_price(obj, variant)
        return str(price) if price is not None else ""

    def get_compare_at_price(self, obj):
        variant = self._selected_variant()
        compare_at = obj.compare_at_price
        if variant is not None and variant.compare_at_price:
            compare_at = variant.compare_at_price
        return format_money(compare_at, self._currency()) if compare_at else ""

    def get_in_stock(self, obj):
        available = _available_quantity(obj)
        if _is_in_stock(available):
            return True
        return any(
            _is_in_stock(_available_quantity(obj, variant))
            for variant in self._active_variants()
        )

    def get_available_quantity(self, obj):
        return _available_quantity(obj)

    def get_currency(self, obj):
        currency = self._currency()
        return {
            "code": currency.code if currency is not None else "",
            "symbol": currency.symbol if currency is not None else "",
            "decimal_places": currency.decimal_places if currency is not None else 0,
        }

    def get_meta_title(self, obj):
        seo = getattr(obj, "seo", None)
        return (seo.meta_title if seo is not None else "") or obj.name

    def get_meta_description(self, obj):
        seo = getattr(obj, "seo", None)
        description = (seo.meta_description if seo is not None else "") or obj.description or ""
        if len(description) > 300:
            return description[:297] + "..."
        return description


class ProductDetailView(APIView):
    """Product detail for the storefront product page."""

    permission_classes = [AllowAny]

    def get(self, request, slug, *args, **kwargs):
        product = (
            Product.objects.filter(slug=slug, is_published=True)
            .select_related("brand", "category", "seo")
            .prefetch_related("images", "variants__attributes__value", "variants__attributes__attribute")
            .first()
        )
        if product is None:
            raise NotFoundError("Product not found", code="catalog.product_not_found")
        currency = get_currency(
            get_active_currency_code(request.COOKIES.get(settings.CURRENCY_COOKIE_NAME))
        )
        serializer = StorefrontProductDetailSerializer(
            product, context={"currency": currency, "product": product}
        )
        return Response(serializer.data)


class PageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Page
        fields = ["id", "title", "slug", "content", "meta_title", "meta_description"]


class BlogPostSerializer(serializers.ModelSerializer):
    class Meta:
        model = BlogPost
        fields = ["id", "title", "slug", "content", "tags", "published_at"]


class BootstrapView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        get_token(request)
        return Response(_storefront_bootstrap(request))


class HookView(APIView):
    """Rendered fragments of enabled plugins for a storefront hook."""

    permission_classes = [AllowAny]

    def get(self, request, hook_name, *args, **kwargs):
        return Response({"hook": hook_name, "fragments": render_plugin_hook(hook_name, request=request)})


class SearchView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        from apps.search.service import search_service

        store = _current_store(request)
        query = (request.query_params.get("q") or "").strip()
        result = search_service.search_products(query, store=store)
        return Response(
            {
                "query": query,
                "total": result.total,
                "results": StorefrontProductSerializer(result.products, many=True).data,
            }
        )


class PageDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, slug, *args, **kwargs):
        page = Page.objects.filter(slug=slug, is_published=True).first()
        if page is None:
            raise NotFoundError("Page not found", code="cms.page_not_found")
        return Response(PageSerializer(page).data)


class BlogListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        posts = BlogPost.objects.filter(is_published=True)
        return Response(BlogPostSerializer(posts, many=True).data)


class BlogDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, slug, *args, **kwargs):
        post = BlogPost.objects.filter(slug=slug, is_published=True).first()
        if post is None:
            raise NotFoundError("Post not found", code="cms.post_not_found")
        return Response(BlogPostSerializer(post).data)


def _product(slug: str) -> Product:
    product = Product.objects.filter(slug=slug).first()
    if product is None:
        raise NotFoundError("Product not found", code="catalog.product_not_found")
    return product


def _compare_identity(request) -> tuple:
    if request.user.is_authenticated:
        return request.user, None
    return None, request.headers.get("X-Cart-Session") or request.session.session_key


class WishlistItemSerializer(serializers.ModelSerializer):
    product = StorefrontProductSerializer(read_only=True)

    class Meta:
        model = WishlistItem
        fields = ["id", "product"]


class CompareItemSerializer(serializers.ModelSerializer):
    product = StorefrontProductSerializer(read_only=True)

    class Meta:
        model = CompareItem
        fields = ["id", "product"]


class WishlistView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        return Response(WishlistItemSerializer(wishlist_for(request.user), many=True).data)

    def post(self, request, *args, **kwargs):
        try:
            add_to_wishlist(request.user, _product(request.data.get("product", "")))
        except ApplicationError:
            pass
        return Response(WishlistItemSerializer(wishlist_for(request.user), many=True).data)


class WishlistDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, product_id, *args, **kwargs):
        remove_from_wishlist(request.user, _product_by_id(product_id))
        return Response(WishlistItemSerializer(wishlist_for(request.user), many=True).data)


class WishlistMoveView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        product = _product(request.data.get("product", ""))
        move_to_cart(request.user, product, store=_current_store(request), quantity=1)
        return Response(WishlistItemSerializer(wishlist_for(request.user), many=True).data)


class CompareView(APIView):
    permission_classes = [AllowAny]

    def _list(self, request):
        user, session_key = _compare_identity(request)
        return compare_list(user=user, session_key=session_key)

    def get(self, request, *args, **kwargs):
        return Response(CompareItemSerializer(self._list(request), many=True).data)

    def post(self, request, *args, **kwargs):
        user, session_key = _compare_identity(request)
        try:
            add_to_compare(_product(request.data.get("product", "")), user=user, session_key=session_key)
        except ApplicationError:
            pass
        return Response(CompareItemSerializer(self._list(request), many=True).data)


class CompareDetailView(APIView):
    permission_classes = [AllowAny]

    def delete(self, request, product_id, *args, **kwargs):
        user, session_key = _compare_identity(request)
        remove_from_compare(_product_by_id(product_id), user=user, session_key=session_key)
        return Response(
            CompareItemSerializer(
                compare_list(user=user, session_key=session_key), many=True
            ).data
        )


def _product_by_id(product_id) -> Product:
    product = Product.objects.filter(pk=product_id).first()
    if product is None:
        raise NotFoundError("Product not found", code="catalog.product_not_found")
    return product
