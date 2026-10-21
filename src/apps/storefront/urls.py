from django.conf import settings
from django.urls import path

from . import views
from .spa import spa_index

app_name = "storefront"


def _plugin_claims(hook):
    """Return True when an enabled plugin renders a storefront hook.

    Used so a plugin (e.g. AjaxCart) can take over a route server-side even when
    the Vue SPA is enabled. Errors are treated as "not claimed" so a broken
    plugin can never break the route.
    """
    if not hook:
        return False
    try:
        from core.plugins.manager import PluginManager

        manager = PluginManager()
        manager.discover_plugins()
        return bool(manager.enabled_storefront_hooks(hook))
    except Exception:
        return False


def spa_page(view, hook=None):
    """Serve the Vue SPA for an interactive route when it is enabled.

    The setting is read per request so the storefront can be switched at runtime
    (and in tests) without reloading URL configuration. Content pages are always
    server-rendered by Django. A route claimed by an enabled plugin hook is
    always server-rendered, bypassing the SPA.
    """

    def dispatch(request, **kwargs):
        if getattr(settings, "STOREFRONT_SPA_ENABLED", False) and not _plugin_claims(hook):
            return spa_index(request, **kwargs)
        return view(request, **kwargs)

    dispatch.__name__ = getattr(view, "__name__", "page")
    return dispatch


urlpatterns = [
    # Content pages: server-rendered (SEO, themes, plugins).
    path("", views.home_view, name="home"),
    path("category/<slug:slug>/", spa_page(views.category_view), name="category"),
    path("product/<slug:slug>/", spa_page(views.product_detail_view), name="product"),
    path("search/", views.search_view, name="search"),
    path("search/autocomplete/", views.autocomplete_view, name="autocomplete"),
    path("search/suggest/", views.suggest_view, name="suggest"),
    path("blog/", views.blog_list_view, name="blog"),
    path("blog/<slug:slug>/", views.blog_detail_view, name="blog_detail"),
    # Interactive pages: Vue SPA (fall back to server rendering when disabled).
    path("cart/", spa_page(views.cart_view, hook="cart_page"), name="cart"),
    path("checkout/", spa_page(views.checkout_view), name="checkout"),
    path("login/", spa_page(views.login_view), name="login"),
    path("register/", spa_page(views.register_view), name="register"),
    path("account/", spa_page(views.account_view), name="account"),
    path("wishlist/", spa_page(views.wishlist_view), name="wishlist"),
    path("compare/", spa_page(views.compare_view), name="compare"),
    path("orders/<str:number>/", spa_page(views.order_detail_view), name="order_detail"),
    # Migrated content routes: Vue SPA, with a server-rendered fallback while
    # the route is being cut over.
    path("brands/", spa_page(views.brand_list_view), name="brands"),
    path("brands/<slug:slug>/", spa_page(views.brand_detail_view), name="brand"),
    # Form actions used by server-rendered pages.
    path("cart/add/<int:product_id>/", views.add_to_cart_view, name="add_to_cart"),
    path("cart/update/<int:item_id>/", views.update_cart_item_view, name="update_cart_item"),
    path("logout/", views.logout_view, name="logout"),
    path("wishlist/add/<int:product_id>/", views.wishlist_add_view, name="wishlist_add"),
    path(
        "wishlist/move/<int:product_id>/",
        views.wishlist_move_to_cart_view,
        name="wishlist_move",
    ),
    path("compare/add/<int:product_id>/", views.compare_add_view, name="compare_add"),
    path("compare/remove/<int:product_id>/", views.compare_remove_view, name="compare_remove"),
    path("robots.txt", views.robots_txt_view, name="robots"),
    path("sitemap.xml", views.sitemap_xml_view, name="sitemap"),
    path("i18n/setlang/", views.set_language_view, name="set_language"),
    path("i18n/setcurrency/", views.set_currency_view, name="set_currency"),
    path("<slug:slug>/", views.cms_page_view, name="cms_page"),
]
