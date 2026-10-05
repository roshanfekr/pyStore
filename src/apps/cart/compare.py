from apps.cart.models import CompareItem
from core.exceptions import ConflictError, ValidationError

MAX_COMPARE_ITEMS = 4


def add_to_compare(product, *, user=None, session_key=None) -> CompareItem:
    if user is None and not session_key:
        raise ValidationError("Compare requires a user or session key", code="compare.identity_required")

    lookup = {"user": user, "product": product} if user else {
        "session_key": session_key, "product": product
    }
    if CompareItem.objects.filter(**lookup).exists():
        raise ConflictError("Product is already in the compare list", code="compare.duplicate")

    identity_filter = {"user": user} if user else {"session_key": session_key}
    count = CompareItem.objects.filter(**identity_filter).count()
    if count >= MAX_COMPARE_ITEMS:
        raise ConflictError(
            f"Compare list is limited to {MAX_COMPARE_ITEMS} products", code="compare.limit"
        )
    return CompareItem.objects.create(**lookup)


def remove_from_compare(product, *, user=None, session_key=None) -> None:
    lookup = {"user": user, "product": product} if user else {
        "session_key": session_key, "product": product
    }
    CompareItem.objects.filter(**lookup).delete()


def compare_list(*, user=None, session_key=None):
    lookup = {"user": user} if user else {"session_key": session_key}
    return CompareItem.objects.filter(**lookup).select_related(
        "product", "product__brand"
    ).order_by("created_at")
