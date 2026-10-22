from django.db.models import Q
from django.utils import timezone
from decimal import Decimal

from apps.catalog.models import Product, ProductVariant
from apps.pricing.models import PriceList, PriceListEntry, ProductPrice, ScheduledPrice


class CurrencyPriceUnavailable(ValueError):
    """No explicit price is configured for the requested currency (FR-CUR-004).

    Subclasses :class:`ValueError` so callers that only distinguish "a price
    could be resolved" from "none could" keep working.
    """


def explicit_currency_price(
    product: Product, variant: ProductVariant | None, currency: str
) -> Decimal | None:
    """Explicitly configured price for the exact product/variant and currency.

    A currency price applies only to the product or variant it is configured
    on (FR-CUR-002): a product-level price is never used as the price of a
    variant of that product, and the other way around.
    """
    code = (currency or "").strip().upper()
    if not code:
        return None
    queryset = ProductPrice.objects.filter(product=product, currency=code)
    row = (
        queryset.filter(variant=variant).first()
        if variant is not None
        else queryset.filter(variant__isnull=True).first()
    )
    return row.price if row is not None else None


def _matching_pricelists(product, variant, customer, store, quantity):
    queryset = PriceList.objects.filter(is_active=True)

    store_filter = Q(store__isnull=True)
    if store is not None:
        store_filter |= Q(store=store)
    queryset = queryset.filter(store_filter)

    customer_filter = Q(customer__isnull=True)
    if customer is not None and getattr(customer, "is_authenticated", False):
        customer_filter |= Q(customer=customer)
    queryset = queryset.filter(customer_filter)

    role_ids = set()
    if customer is not None and getattr(customer, "is_authenticated", False):
        role_ids = set(customer.roles.values_list("id", flat=True))

    scored = []
    for price_list in queryset:
        score = 0
        if customer is not None and price_list.customer_id == getattr(customer, "id", None):
            score += 4
        if price_list.role_id and price_list.role_id in role_ids:
            score += 2
        if price_list.store_id:
            score += 1
        scored.append((score, price_list.priority, price_list))

    scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return [price_list for _, _, price_list in scored]


def _entry_price(price_list, product, variant, quantity):
    target = Q()
    if variant is not None:
        target = Q(variant=variant)
    else:
        target = Q(product=product, variant__isnull=True)

    entries = PriceListEntry.objects.filter(
        price_list=price_list,
        min_quantity__lte=quantity,
    ).filter(target)
    entries = entries.filter(Q(max_quantity__isnull=True) | Q(max_quantity__gte=quantity))

    variant_entry = entries.filter(variant=variant).first() if variant else None
    if variant_entry:
        return variant_entry.price
    entry = entries.order_by("-min_quantity").first()
    return entry.price if entry else None


def pricing_provider(product: Product, variant: ProductVariant | None = None, context: dict | None = None):
    context = context or {}
    customer = context.get("customer")
    store = context.get("store")
    quantity = int(context.get("quantity") or 1)
    currency = (context.get("currency") or "").strip().upper()
    base_currency = (getattr(store, "default_currency", "") or "").strip().upper()

    base = variant.price if variant is not None else product.price
    if base is None:
        raise ValueError(f"Product {product.pk} has no price configured")

    if currency and currency != base_currency:
        # Only an explicitly configured price is usable in another currency;
        # the base-currency price is never an implicit conversion source
        # (FR-CUR-004). Price list and scheduled prices are base-currency
        # constructs and are not applied to other currencies.
        explicit = explicit_currency_price(product, variant, currency)
        if explicit is None:
            raise CurrencyPriceUnavailable(
                f"Product {product.pk} has no price configured for {currency}"
            )
        return explicit

    for price_list in _matching_pricelists(product, variant, customer, store, quantity):
        price = _entry_price(price_list, product, variant, quantity)
        if price is not None:
            return price

    now = timezone.now()
    scheduled = ScheduledPrice.objects.filter(
        is_active=True, start_at__lte=now
    ).filter(Q(end_at__isnull=True) | Q(end_at__gte=now))
    if variant is not None:
        scheduled = scheduled.filter(variant=variant)
    else:
        scheduled = scheduled.filter(product=product, variant__isnull=True)

    scheduled_price = scheduled.first()
    if scheduled_price is not None:
        return scheduled_price.price

    # An explicit price for the base currency replaces the stored base price
    # when no price list or scheduled price applies to it.
    if currency or base_currency:
        explicit = explicit_currency_price(product, variant, currency or base_currency)
        if explicit is not None:
            return explicit

    return base


def resolve_product_price(
    product: Product,
    variant: ProductVariant | None = None,
    *,
    customer=None,
    store=None,
    quantity: int = 1,
    currency: str | None = None,
):
    from apps.catalog.pricing import pricing_registry

    return pricing_registry.resolve(
        product,
        variant,
        context={"customer": customer, "store": store, "quantity": quantity, "currency": currency},
    )
