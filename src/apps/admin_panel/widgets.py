from django import forms

from apps.catalog.models import Tag


class TagPickerWidget(forms.TextInput):
    """Free-text tag input powered by the vendored Tagify library.

    The submitted value stays a plain comma-separated string (Tagify's
    ``originalInputValueFormat``), so ``ProductAdminForm.clean_tags_input`` and
    ``ProductAdmin.save_related`` keep working unchanged. All JavaScript lives
    in external files because the site Content-Security-Policy
    (``script-src 'self'``) blocks inline ``<script>`` blocks.
    """

    template_name = "admin_panel/widgets/tag_picker.html"

    class Media:
        css = {"all": ("admin_panel/vendor/tagify/tagify.css",)}
        js = (
            "admin_panel/vendor/tagify/tagify.min.js",
            "admin_panel/js/tagify_init.js",
        )

    def format_value(self, value):
        if value is None:
            return ""
        if isinstance(value, (list, tuple)):
            return ", ".join(str(item) for item in value)
        return str(value)

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        widget = context["widget"]
        widget["value"] = self.format_value(value)
        # Keep the marker class that ``tagify_init.js`` looks for.
        css = (widget["attrs"].get("class") or "").split()
        if "ps-tagify" not in css:
            css.append("ps-tagify")
        widget["attrs"]["class"] = " ".join(css)
        # ``json_script`` JSON-encodes this list for us; do NOT pre-encode it.
        context["all_tags"] = sorted(set(Tag.objects.values_list("name", flat=True)))
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
