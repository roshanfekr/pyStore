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
