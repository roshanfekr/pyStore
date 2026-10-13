from django.conf import settings

from apps.cart.compare import CompareItem
from apps.cart.wishlist import WishlistItem
from apps.cms.models import Menu, Widget
from apps.storefront.themes import get_active_theme_name, get_theme_config
from apps.stores.services import (
    get_active_currencies,
    get_active_currency_code,
    get_active_languages,
    get_currency,
    get_language,
)


def storefront(request):
    from django.utils import translation

    branding = get_theme_config()
    branding.setdefault("site_name", "pyStore")

    menu_items = []
    menu = Menu.objects.filter(slug="main").first()
    if menu is not None:
        menu_items = list(
            menu.items.filter(parent__isnull=True).order_by("ordering")
        )

    widgets = list(Widget.objects.filter(is_active=True).order_by("name")[:5])

    active_code = translation.get_language() or "en"
    active_language = get_language(active_code)
    languages = get_active_languages()

    active_currency_code = get_active_currency_code(
        request.COOKIES.get(settings.CURRENCY_COOKIE_NAME)
    )
    active_currency = get_currency(active_currency_code)
    currencies = get_active_currencies()

    context = {
        "theme": get_active_theme_name(),
        "branding": branding,
        "menu_items": menu_items,
        "widgets": widgets,
        "wishlist_count": 0,
        "compare_count": 0,
        "languages": [
            {
                "code": language.code,
                "name": language.name,
                "flag": language.flag,
                "direction": language.direction,
                "is_current": language.code == active_code,
            }
            for language in languages
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
    }

    if request.user.is_authenticated:
        context["wishlist_count"] = WishlistItem.objects.filter(user=request.user).count()
        context["compare_count"] = CompareItem.objects.filter(user=request.user).count()

    return {"storefront": context}
