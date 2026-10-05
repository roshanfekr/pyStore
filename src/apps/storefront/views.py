
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from apps.cart.compare import add_to_compare, compare_list, remove_from_compare
from apps.cart.services import (
    add_to_cart,
    calculate,
    get_cart,
    get_or_create_cart,
    merge_guest_cart,
    update_item_quantity,
)
from apps.cart.wishlist import (
    add_to_wishlist,
    move_to_cart,
    wishlist_for,
)
from apps.catalog.models import Category
from apps.catalog.services import resolve_price
from apps.checkout.models import PaymentMethod, ShippingMethod
from apps.checkout.services import execute_checkout
from apps.cms.models import BlogPost, Page
from apps.cms.seo import build_robots_txt, build_sitemap_items, get_seo_metadata
from apps.identity.services.registration import register_customer
from apps.orders.models import Order
from apps.stores.services import ensure_default_store, get_store_by_domain
from core.exceptions import ApplicationError


def _current_store(request):
    host = request.get_host().split(":")[0]
    try:
        return get_store_by_domain(host)
    except Exception:
        pass

    from apps.stores.models import Store

    store = Store.objects.filter(is_default=True).first() or Store.objects.first()
    return store if store is not None else ensure_default_store()


def _session_cart(request, store):
    if request.user.is_authenticated:
        return get_or_create_cart(store, user=request.user)
    if not request.session.session_key:
        request.session.create()
    return get_or_create_cart(store, session_key=request.session.session_key)


def home_view(request):
    store = _current_store(request)
    products = store.products.filter(is_published=True).order_by("-created_at")[:12]
    return render(request, "storefront/home.html", {"products": products})


def category_view(request, slug):
    store = _current_store(request)
    category = get_object_or_404(
        Category, slug=slug, is_active=True
    )
    category_ids = [category.id, *category.descendant_ids()]
    products = store.products.filter(
        is_published=True, category_id__in=category_ids
    )
    return render(request, "storefront/category.html", {"category": category, "products": products})


def product_detail_view(request, slug):
    store = _current_store(request)
    product = get_object_or_404(
        store.products.select_related("brand", "category", "seo"), slug=slug, is_published=True
    )
    variants = product.variants.filter(is_active=True)
    price = resolve_price(product, variants.first() if variants.exists() else None)
    seo = get_seo_metadata(product, request.build_absolute_uri("/").rstrip("/"))
    return render(
        request,
        "storefront/product_detail.html",
        {"product": product, "variants": variants, "price": price, "seo": seo},
    )


def search_view(request):
    store = _current_store(request)
    query = (request.GET.get("q") or "").strip()
    from apps.search.service import search_service

    result = search_service.search_products(query, store=store)
    return render(
        request,
        "storefront/search.html",
        {"query": query, "products": result.products, "total": result.total},
    )


def autocomplete_view(request):
    store = _current_store(request)
    query = (request.GET.get("q") or "").strip()
    from django.http import JsonResponse

    from apps.search.service import search_service

    return JsonResponse(
        {"results": search_service.autocomplete(query, store=store)},
        safe=False,
    )


def suggest_view(request):
    store = _current_store(request)
    query = (request.GET.get("q") or "").strip()
    from django.http import JsonResponse

    from apps.search.service import search_service

    return JsonResponse(
        {"suggestions": search_service.suggest(query, store=store)},
        safe=False,
    )


def cart_view(request):
    store = _current_store(request)
    cart = get_cart(
        store,
        user=request.user if request.user.is_authenticated else None,
        session_key=request.session.session_key,
    )
    calculation = calculate(cart, customer=request.user if request.user.is_authenticated else None) if cart else None
    return render(request, "storefront/cart.html", {"cart": cart, "calculation": calculation})


def add_to_cart_view(request, product_id):
    store = _current_store(request)
    cart = _session_cart(request, store)
    try:
        add_to_cart(cart, store.products.get(pk=product_id, is_published=True), 1)
    except ApplicationError:
        pass
    return redirect("storefront:cart")


def update_cart_item_view(request, item_id):
    store = _current_store(request)
    cart = get_cart(
        store,
        user=request.user if request.user.is_authenticated else None,
        session_key=request.session.session_key,
    )
    if cart is not None:
        try:
            update_item_quantity(cart, item_id, int(request.POST.get("quantity", 1)))
        except (ApplicationError, ValueError):
            pass
    return redirect("storefront:cart")


def checkout_view(request):
    store = _current_store(request)
    cart = get_cart(
        store,
        user=request.user if request.user.is_authenticated else None,
        session_key=request.session.session_key,
    )
    if cart is None or not cart.items.exists():
        return redirect("storefront:cart")

    customer = request.user if request.user.is_authenticated else None
    if request.method == "POST":
        address = {
            "first_name": request.POST.get("first_name", ""),
            "last_name": request.POST.get("last_name", ""),
            "country": request.POST.get("country", ""),
            "state": request.POST.get("state", ""),
            "city": request.POST.get("city", ""),
            "postal_code": request.POST.get("postal_code", ""),
            "address_line": request.POST.get("address_line", ""),
            "phone": request.POST.get("phone", ""),
        }
        try:
            order = execute_checkout(
                cart,
                user=request.user if request.user.is_authenticated else None,
                email=request.POST.get("email", ""),
                shipping_address=address,
                shipping_method_code=request.POST.get("shipping_method", ""),
                payment_method_code=request.POST.get("payment_method", ""),
            )
            return render(request, "storefront/order_detail.html", {"order": order})
        except ApplicationError as exc:
            error = exc.message
    else:
        error = None

    calculation = calculate(cart, customer=customer)
    shipping_methods = ShippingMethod.objects.filter(store=store, is_active=True)
    payment_methods = PaymentMethod.objects.filter(is_active=True)
    return render(
        request,
        "storefront/checkout.html",
        {
            "cart": cart,
            "calculation": calculation,
            "shipping_methods": shipping_methods,
            "payment_methods": payment_methods,
            "error": error,
        },
    )


def register_view(request):
    if request.method == "POST":
        email = request.POST.get("email", "")
        password = request.POST.get("password", "")
        result = register_customer(email=email, password=password)
        if result:
            user = authenticate(request, email=email, password=password)
            if user is not None:
                login(request, user)
            return redirect("storefront:account")
        error = result.error.message
    else:
        error = None
    return render(request, "storefront/register.html", {"error": error})


def login_view(request):
    if request.method == "POST":
        user = authenticate(
            request,
            email=request.POST.get("email", ""),
            password=request.POST.get("password", ""),
        )
        if user is not None:
            login(request, user)
            merge_guest_cart(_current_store(request), request.session.session_key, user)
            return redirect("storefront:account")
        error = "Invalid email or password"
    else:
        error = None
    return render(request, "storefront/login.html", {"error": error})


def logout_view(request):
    logout(request)
    return redirect("storefront:home")


@login_required
def account_view(request):
    orders = Order.objects.filter(user=request.user)[:10]
    return render(request, "storefront/account.html", {"orders": orders})


@login_required
def wishlist_view(request):
    items = wishlist_for(request.user)
    return render(request, "storefront/wishlist.html", {"items": items})


@login_required
def wishlist_add_view(request, product_id):
    store = _current_store(request)
    try:
        add_to_wishlist(request.user, store.products.get(pk=product_id, is_published=True))
    except ApplicationError:
        pass
    return redirect("storefront:wishlist")


@login_required
def wishlist_move_to_cart_view(request, product_id):
    store = _current_store(request)
    try:
        move_to_cart(request.user, store.products.get(pk=product_id), store=store, quantity=1)
    except ApplicationError:
        pass
    return redirect("storefront:wishlist")


@login_required
def compare_view(request):
    items = compare_list(user=request.user)
    return render(request, "storefront/compare.html", {"items": items})


@login_required
def compare_add_view(request, product_id):
    store = _current_store(request)
    try:
        add_to_compare(store.products.get(pk=product_id, is_published=True), user=request.user)
    except ApplicationError:
        pass
    return redirect("storefront:compare")


@login_required
def compare_remove_view(request, product_id):
    from apps.catalog.models import Product

    product = Product.objects.filter(pk=product_id).first()
    if product is not None:
        remove_from_compare(product, user=request.user)
    return redirect("storefront:compare")


@login_required
def order_detail_view(request, number):
    order = Order.objects.filter(number=number).first()
    if order is None or (order.user_id != request.user.id and not request.user.is_staff):
        raise Http404("Order not found")
    return render(request, "storefront/order_detail.html", {"order": order})


def cms_page_view(request, slug):
    page = get_object_or_404(Page, slug=slug, is_published=True)
    seo = get_seo_metadata(page, request.build_absolute_uri("/").rstrip("/"))
    return render(request, "storefront/cms_page.html", {"page": page, "seo": seo})


def blog_list_view(request):
    posts = BlogPost.objects.filter(is_published=True)
    return render(request, "storefront/blog_list.html", {"posts": posts})


def blog_detail_view(request, slug):
    post = get_object_or_404(BlogPost, slug=slug, is_published=True)
    seo = get_seo_metadata(post, request.build_absolute_uri("/").rstrip("/"))
    return render(request, "storefront/blog_detail.html", {"post": post, "seo": seo})


def robots_txt_view(request):
    return HttpResponse(
        build_robots_txt(request.build_absolute_uri("/").rstrip("/")),
        content_type="text/plain",
    )


def sitemap_xml_view(request):
    base_url = request.build_absolute_uri("/").rstrip("/")
    items = build_sitemap_items(base_url=base_url)
    entries = "".join(
        f"<url><loc>{item['loc']}</loc><priority>{item['priority']}</priority></url>"
        for item in items
    )
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        f"{entries}</urlset>"
    )
    return HttpResponse(xml, content_type="application/xml")
