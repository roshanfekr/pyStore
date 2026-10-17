from django import template

from apps.stores.services import get_active_currency_code, get_currency

register = template.Library()


@register.simple_tag(takes_context=True)
def ajax_cart_currency(context) -> dict:
    """Active currency (code, symbol, decimals) for client-side money rendering.

    Mirrors the storefront context processor so the AJAX cart formats amounts
    with the same currency the server-rendered pages use.
    """
    from django.conf import settings

    request = context.get("request")
    cookie_code = None
    if request is not None:
        cookie_code = request.COOKIES.get(settings.CURRENCY_COOKIE_NAME)

    code = get_active_currency_code(cookie_code)
    currency = get_currency(code)
    try:
        decimals = int(getattr(currency, "decimal_places", 0) or 0)
    except (TypeError, ValueError):
        decimals = 0
    return {
        "code": code,
        "symbol": getattr(currency, "symbol", "") or "",
        "decimal_places": decimals,
    }
