from django.urls import path

from . import views

app_name = "storefront"

urlpatterns = [
    path("", views.home_view, name="home"),
    path("category/<slug:slug>/", views.category_view, name="category"),
    path("product/<slug:slug>/", views.product_detail_view, name="product"),
    path("search/", views.search_view, name="search"),
    path("search/autocomplete/", views.autocomplete_view, name="autocomplete"),
    path("search/suggest/", views.suggest_view, name="suggest"),
    path("cart/", views.cart_view, name="cart"),
    path("cart/add/<uuid:product_id>/", views.add_to_cart_view, name="add_to_cart"),
    path("cart/update/<uuid:item_id>/", views.update_cart_item_view, name="update_cart_item"),
    path("checkout/", views.checkout_view, name="checkout"),
    path("login/", views.login_view, name="login"),
    path("register/", views.register_view, name="register"),
    path("logout/", views.logout_view, name="logout"),
    path("account/", views.account_view, name="account"),
    path("wishlist/", views.wishlist_view, name="wishlist"),
    path("wishlist/add/<uuid:product_id>/", views.wishlist_add_view, name="wishlist_add"),
    path(
        "wishlist/move/<uuid:product_id>/",
        views.wishlist_move_to_cart_view,
        name="wishlist_move",
    ),
    path("compare/", views.compare_view, name="compare"),
    path("compare/add/<uuid:product_id>/", views.compare_add_view, name="compare_add"),
    path("compare/remove/<uuid:product_id>/", views.compare_remove_view, name="compare_remove"),
    path("orders/<str:number>/", views.order_detail_view, name="order_detail"),
    path("blog/", views.blog_list_view, name="blog"),
    path("blog/<slug:slug>/", views.blog_detail_view, name="blog_detail"),
    path("robots.txt", views.robots_txt_view, name="robots"),
    path("sitemap.xml", views.sitemap_xml_view, name="sitemap"),
    path("<slug:slug>/", views.cms_page_view, name="cms_page"),
]
