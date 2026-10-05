from apps.checkout.steps import (
    AddressStep,
    CustomerStep,
    DiscountStep,
    InventoryStep,
    OrderCreationStep,
    PaymentStep,
    ShippingStep,
    TaxStep,
    ValidateCartStep,
)


def default_steps():
    return [
        ValidateCartStep(),
        CustomerStep(),
        AddressStep(),
        ShippingStep(),
        TaxStep(),
        DiscountStep(),
        InventoryStep(),
        PaymentStep(),
        OrderCreationStep(),
    ]


class CheckoutPipeline:
    """Ordered checkout steps. Plugins can inject steps at any position."""

    def __init__(self, steps=None):
        self._steps = list(steps) if steps is not None else default_steps()

    def steps(self) -> list:
        return list(self._steps)

    def step_names(self) -> list[str]:
        return [step.name for step in self._steps]

    def register_before(self, existing_name: str, step) -> None:
        index = self._index_of(existing_name)
        self._steps.insert(index, step)

    def register_after(self, existing_name: str, step) -> None:
        index = self._index_of(existing_name)
        self._steps.insert(index + 1, step)

    def append(self, step) -> None:
        self._steps.append(step)

    def remove(self, name: str) -> None:
        del self._steps[self._index_of(name)]

    def _index_of(self, name: str) -> int:
        for index, step in enumerate(self._steps):
            if step.name == name:
                return index
        raise ValueError(f"Checkout step {name!r} not found")

    def run(self, context) -> None:
        for step in self._steps:
            step.run(context)
