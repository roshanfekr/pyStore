from apps.cart.compare import CompareItem
from apps.cart.wishlist import WishlistItem
from apps.cms.models import Menu, Widget
from apps.storefront.themes import get_active_theme_name, get_theme_config


def storefront(request):
    branding = get_theme_config()
    branding.setdefault("site_name", "pyStore")

    menu_items = []
    menu = Menu.objects.filter(slug="main").first()
    if menu is not None:
        menu_items = list(
            menu.items.filter(parent__isnull=True).order_by("ordering")
        )

    widgets = list(Widget.objects.filter(is_active=True).order_by("name")[:5])

    context = {
        "theme": get_active_theme_name(),
        "branding": branding,
        "menu_items": menu_items,
        "widgets": widgets,
        "wishlist_count": 0,
        "compare_count": 0,
    }

    if request.user.is_authenticated:
        context["wishlist_count"] = WishlistItem.objects.filter(user=request.user).count()
        context["compare_count"] = CompareItem.objects.filter(user=request.user).count()

    return {"storefront": context}
