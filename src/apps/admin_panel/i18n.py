"""Namespaced translation keys for admin form labels.

Model field labels come from Django's ``verbose_name`` and are *not* passed
through the ``{% tr %}`` template tag. On top of that, the DB word collection
(``LocaleStringResource``) is keyed by the English source string and matched
case-insensitively, so short generic labels such as "Name", "Status" or
"Price" collide with unrelated storefront strings.

To keep the admin's product definition translatable without those collisions
every label gets a unique, namespaced key::

    admin.form.<app_label>.<model_name>.<field_name>

The Persian values for those keys live in
:data:`apps.stores.seed_translations.PERSIAN_STRINGS` and are seeded by the
``seed_translations`` management command and by migration ``stores.0003``.

When no entry exists for the active language (e.g. English) the *original*
label is kept, so the admin never shows a raw namespaced key.
"""
from django.db import OperationalError, ProgrammingError
from django.utils import translation

from apps.stores.services import _catalog_for, lookup_translation


def field_key(model, field_name: str) -> str:
    """Return the unique translation key for ``model.field_name``."""
    meta = model._meta
    return f"admin.form.{meta.app_label}.{meta.model_name}.{field_name}"


def _lookup_optional(key: str) -> str | None:
    """Return the translation for ``key`` or ``None`` when it is missing.

    The catalog lookup queries ``LocaleStringResource``. System checks and
    admin autodiscovery run before migrations exist on a fresh database, so a
    missing table (or otherwise unavailable catalog) must fall back to the
    original label instead of breaking management commands such as
    ``migrate`` and ``makemigrations``.
    """
    try:
        value = _catalog_for(translation.get_language() or "en").get(
            (key or "").strip().casefold(), ""
        )
    except (OperationalError, ProgrammingError):
        return None
    value = value.strip()
    return value or None


def translate_field(model, field_name: str) -> str | None:
    """Translated label for ``model.field_name``, or ``None`` if unavailable."""
    return _lookup_optional(field_key(model, field_name))


def translate_form_labels(form, model) -> None:
    """Translate every field label of ``form`` for ``model`` in place.

    Called from a form's ``__init__``; Django deep-copies ``base_fields`` into
    ``self.fields`` per instance, so this never leaks between requests or
    languages. Fields without an entry keep their original (English) label.
    """
    for name, field in form.fields.items():
        translated = translate_field(model, name)
        if translated:
            field.label = translated


def translate_help_text(form, model, field_name: str, key: str) -> None:
    """Translate a single field's help text from an explicit key."""
    if field_name not in form.fields:
        return
    translated = _lookup_optional(key)
    if translated:
        form.fields[field_name].help_text = translated


def translate_text(key: str, default: str) -> str:
    """Translate admin template text from a namespaced ``key``.

    The word collection is matched case-insensitively on the English source
    string, so a source string shared with the storefront (for example
    "No orders yet.") can only carry one translation. Admin text that
    collides with a storefront string therefore uses a namespaced key
    (``admin.<area>.<name>``) and keeps its own original text as fallback,
    exactly like the form labels handled by :func:`translate_field`.
    """
    return _lookup_optional(key) or default


__all__ = [
    "field_key",
    "lookup_translation",
    "translate_field",
    "translate_form_labels",
    "translate_help_text",
    "translate_text",
]
