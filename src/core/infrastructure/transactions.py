from typing import Any, Callable

from django.db import transaction


def atomic(*args, **kwargs):
    return transaction.atomic(*args, **kwargs)


def run_in_transaction(func: Callable[..., Any], *args, **kwargs) -> Any:
    with transaction.atomic():
        return func(*args, **kwargs)
