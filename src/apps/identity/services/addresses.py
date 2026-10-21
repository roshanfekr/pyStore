"""Address-book rules for the customer-owned saved address entity.

Ownership rules (FR-CUST-002): a saved address belongs to exactly one
customer, only that customer may read or change it, and at most one of a
customer's addresses is the default. The order address snapshot is a separate
entity, so changing or deleting a saved address never alters an existing
order.
"""

from apps.identity.models import Address
from core.exceptions import NotFoundError
from core.infrastructure import atomic


def list_addresses(customer):
    """Return the customer's own saved addresses."""
    return customer.addresses.all()


def get_address(customer, address_id):
    """Return one of the customer's own addresses, or raise NotFoundError.

    A missing address and an address owned by another customer are
    indistinguishable to the caller, so no other customer's address data is
    exposed.
    """
    address = customer.addresses.filter(pk=address_id).first()
    if address is None:
        raise NotFoundError("Address not found", code="identity.address_not_found")
    return address


@atomic()
def create_address(customer, *, is_default: bool = False, **fields):
    """Create a saved address for the customer.

    A customer has at most one default address, so creating a default address
    clears the previous default.
    """
    if is_default:
        Address.objects.filter(customer=customer, is_default=True).update(is_default=False)
    return Address.objects.create(customer=customer, is_default=is_default, **fields)


@atomic()
def update_address(address, *, is_default=None, **fields):
    """Update a saved address, keeping the single-default rule."""
    if is_default is True:
        Address.objects.filter(customer=address.customer, is_default=True).exclude(
            pk=address.pk
        ).update(is_default=False)
    for field, value in fields.items():
        setattr(address, field, value)
    if is_default is not None:
        address.is_default = is_default
    address.save()
    return address


@atomic()
def delete_address(address):
    """Remove a saved address from the customer's address book."""
    address.delete()
    return address
