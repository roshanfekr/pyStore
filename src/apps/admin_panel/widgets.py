import json

from django import forms

from apps.catalog.models import Tag


class TagPickerWidget(forms.TextInput):
    """Free-text tag picker: type, get chips, autocomplete existing tags.

    The actual form value is a comma-separated string of tag names stored in
    a hidden input; the visible input only collects new entries.
    """

    template_name = "admin_panel/widgets/tag_picker.html"

    def format_value(self, value):
        if value is None:
            return ""
        if isinstance(value, (list, tuple)):
            return ", ".join(str(item) for item in value)
        return str(value)

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context["widget"]["value"] = self.format_value(value)
        context["all_tags"] = json.dumps(
            sorted(set(Tag.objects.values_list("name", flat=True)))
        )
        return context


class SearchableSelectWidget(forms.Select):
    """A plain ``<select>`` that is upgraded into a searchable combobox.

    The markup stays a native select so that form submission, validation and
    Django's admin "add related" popups keep working unchanged; the external
    script ``admin_panel/js/searchable_select.js`` progressively enhances every
    element carrying the ``ps-search-select`` class into a Bootstrap 5 dropdown
    with a live text filter.
    """

    def __init__(self, attrs=None, choices=()):
        final_attrs = {"class": "ps-search-select"}
        if attrs:
            final_attrs.update(attrs)
            if attrs.get("class"):
                final_attrs["class"] = "ps-search-select " + attrs["class"]
        super().__init__(final_attrs, choices)
