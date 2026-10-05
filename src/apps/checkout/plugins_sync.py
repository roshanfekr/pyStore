from decimal import Decimal

from apps.checkout.models import PaymentMethod, ShippingMethod


def sync_payment_methods() -> int:
    """Create PaymentMethod rows for every registered payment gateway plugin."""
    from core.payments.registry import payment_gateway_registry

    created = 0
    for gateway in payment_gateway_registry.all():
        _, was_created = PaymentMethod.objects.get_or_create(
            code=gateway.code,
            defaults={"name": gateway.name, "description": "Payment gateway plugin"},
        )
        if was_created:
            created += 1
    return created


def sync_shipping_methods(store) -> int:
    """Create/update ShippingMethod rows from registered shipping provider plugins."""
    from core.shipping.registry import shipping_provider_registry

    created = 0
    for provider in shipping_provider_registry.all():
        for rate in provider.get_rates({}):
            _, was_created = ShippingMethod.objects.update_or_create(
                store=store,
                code=rate["code"],
                defaults={
                    "name": rate.get("name", rate["code"]),
                    "flat_price": Decimal(str(rate["price"])),
                    "provider_code": provider.code,
                    "is_active": True,
                },
            )
            if was_created:
                created += 1
    return created


def deactivate_provider_shipping_methods(provider_code: str) -> None:
    ShippingMethod.objects.filter(provider_code=provider_code).update(is_active=False)
