from decimal import Decimal

from django.db.models import Q

from apps.pricing.models import CustomerTaxInfo, TaxClass, TaxRate

DEFAULT_TAX_CLASS_NAME = "Standard"


def ensure_default_tax_class() -> TaxClass:
    tax_class = TaxClass.objects.filter(name=DEFAULT_TAX_CLASS_NAME).first()
    if tax_class is None:
        tax_class = TaxClass.objects.create(name=DEFAULT_TAX_CLASS_NAME, is_default=True)
    return tax_class


def create_tax_rate(tax_class, name: str, rate, *, country: str = "", state: str = "") -> TaxRate:
    return TaxRate.objects.create(
        tax_class=tax_class, name=name, rate=rate, country=country.upper(), state=state
    )


def get_product_tax_class(product) -> TaxClass:
    from apps.pricing.models import ProductTaxSetting

    mapping = ProductTaxSetting.objects.filter(product=product).select_related("tax_class").first()
    if mapping is not None:
        return mapping.tax_class
    tax_class = TaxClass.objects.filter(is_default=True).first()
    if tax_class is None:
        tax_class = ensure_default_tax_class()
    return tax_class


def set_product_tax_class(product, tax_class) -> None:
    from apps.pricing.models import ProductTaxSetting

    ProductTaxSetting.objects.update_or_create(product=product, defaults={"tax_class": tax_class})


def is_customer_tax_exempt(customer) -> bool:
    if customer is None or not getattr(customer, "is_authenticated", False):
        return False
    info = CustomerTaxInfo.objects.filter(user=customer).first()
    return bool(info and info.tax_exempt)


def resolve_tax_rate(tax_class: TaxClass, country: str = "", state: str = "") -> TaxRate | None:
    country = (country or "").upper()
    state = (state or "").upper()

    rates = TaxRate.objects.filter(tax_class=tax_class, is_active=True)

    candidates = list(
        rates.filter(Q(country="") | Q(country=country)).filter(Q(state="") | Q(state=state))
    )
    if not candidates:
        return None

    def specificity(rate: TaxRate) -> tuple:
        return (bool(rate.country), bool(rate.state))

    candidates.sort(key=specificity, reverse=True)

    if state:
        state_matches = [r for r in candidates if r.country == country and r.state == state]
        if state_matches:
            return state_matches[0]
    country_matches = [r for r in candidates if r.country == country and not r.state]
    if country_matches:
        return country_matches[0]
    global_rates = [r for r in candidates if not r.country and not r.state]
    return global_rates[0] if global_rates else None


def calculate_tax(
    amount,
    *,
    product=None,
    tax_class: TaxClass | None = None,
    country: str = "",
    state: str = "",
    customer=None,
) -> dict:
    amount = Decimal(amount)
    if is_customer_tax_exempt(customer):
        return {"tax_amount": Decimal("0.0000"), "rate": Decimal("0"), "tax_class": None, "exempt": True}

    if tax_class is None and product is not None:
        tax_class = get_product_tax_class(product)
    if tax_class is None:
        tax_class = ensure_default_tax_class()

    rate = resolve_tax_rate(tax_class, country=country, state=state)
    if rate is None:
        return {"tax_amount": Decimal("0.0000"), "rate": Decimal("0"), "tax_class": tax_class.name, "exempt": False}

    tax_amount = (amount * rate.rate / Decimal("100")).quantize(Decimal("0.0001"))
    return {
        "tax_amount": tax_amount,
        "rate": rate.rate,
        "tax_class": tax_class.name,
        "exempt": False,
    }
