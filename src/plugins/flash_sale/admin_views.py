import uuid
from functools import wraps

from django import forms
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.http import Http404
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils import timezone

from apps.catalog.models import Product
from core.exceptions import ApplicationError
from plugins.flash_sale.models import FlashSaleProduct
from plugins.flash_sale.services import create_flash_sale, update_flash_sale

PLUGIN_ID = "flash_sale"


def _t(request, key: str) -> str:
    """Translate via the language word collection."""
    from apps.stores.services import lookup_translation

    return lookup_translation(request.LANGUAGE_CODE, key)


def plugin_enabled_required(view):
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        from core.plugins.manager import PluginManager

        manager = PluginManager()
        manager.discover_plugins()
        if not manager.is_plugin_enabled(PLUGIN_ID):
            raise Http404(f"Plugin {PLUGIN_ID!r} is not enabled")
        return view(request, *args, **kwargs)

    return wrapper


class SaleForm(forms.Form):
    product = forms.ModelChoiceField(
        queryset=Product.objects.filter(is_published=True).order_by("name"), label="Product"
    )
    discount_percent = forms.DecimalField(
        max_digits=5, decimal_places=2, min_value=0, max_value=100, label="Discount (%)"
    )
    start_at = forms.DateTimeField(
        label="Starts at",
        input_formats=["%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M"],
    )
    end_at = forms.DateTimeField(
        label="Ends at",
        input_formats=["%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M"],
    )
    quantity = forms.IntegerField(min_value=0, initial=0, label="Quantity limit", help_text="0 = unlimited")
    is_active = forms.BooleanField(required=False, initial=True, label="Active")

    def clean(self):
        cleaned = super().clean()
        start_at, end_at = cleaned.get("start_at"), cleaned.get("end_at")
        if start_at and end_at and end_at <= start_at:
            self.add_error("end_at", "End must be after start.")
        return cleaned


def _translate_labels(form, language_code: str):
    """Translate form field labels through the language word collection."""
    from apps.stores.services import lookup_translation

    for field_name, field in form.fields.items():
        field.label = lookup_translation(language_code, str(field.label))


@plugin_enabled_required
@staff_member_required
def sale_list_view(request):
    now = timezone.now()
    sales = list(FlashSaleProduct.objects.select_related("product"))
    running = [sale for sale in sales if sale.is_active and sale.start_at <= now <= sale.end_at]
    upcoming = [sale for sale in sales if sale.is_active and sale.start_at > now]
    ended = [sale for sale in sales if sale.is_active and sale.end_at < now]
    inactive = [sale for sale in sales if not sale.is_active]

    context = {
        "title": _t(request, "Flash sales"),
        "groups": [
            ("Running now", running),
            ("Upcoming", upcoming),
            ("Ended", ended),
            ("Inactive", inactive),
        ],
        "add_url": reverse("pystore_admin:flash_sale_add"),
    }
    return TemplateResponse(request, "flash_sale/admin/list.html", context)


@plugin_enabled_required
@staff_member_required
def sale_edit_view(request, sale_id: uuid.UUID | None = None):
    sale = FlashSaleProduct.objects.filter(pk=sale_id).select_related("product").first() if sale_id else None

    if request.method == "POST":
        form = SaleForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            try:
                if sale is None:
                    create_flash_sale(
                        data["product"].id,
                        discount_percent=data["discount_percent"],
                        start_at=data["start_at"],
                        end_at=data["end_at"],
                        quantity=data["quantity"],
                        is_active=data["is_active"],
                    )
                else:
                    update_flash_sale(
                        sale,
                        product_id=data["product"].id,
                        discount_percent=data["discount_percent"],
                        start_at=data["start_at"],
                        end_at=data["end_at"],
                        quantity=data["quantity"],
                        is_active=data["is_active"],
                    )
                messages.success(request, _t(request, "Flash sale saved."))
                return redirect("pystore_admin:flash_sale_list")
            except ApplicationError as exc:
                messages.error(request, str(getattr(exc, "message", exc)))
        else:
            messages.error(request, _t(request, "Please fix the errors below."))
    else:
        form = SaleForm(
            initial={}
            if sale is None
            else {
                "product": sale.product_id,
                "discount_percent": sale.discount_percent,
                "start_at": sale.start_at,
                "end_at": sale.end_at,
                "quantity": sale.quantity,
                "is_active": sale.is_active,
            }
        )
    _translate_labels(form, request.LANGUAGE_CODE)

    context = {
        "title": _t(request, "Edit flash sale" if sale else "Add flash sale"),
        "form": form,
        "sale": sale,
        "list_url": reverse("pystore_admin:flash_sale_list"),
    }
    return TemplateResponse(request, "flash_sale/admin/edit.html", context)


@plugin_enabled_required
@staff_member_required
def sale_delete_view(request, sale_id: uuid.UUID):
    sale = FlashSaleProduct.objects.filter(pk=sale_id).first()
    if sale is not None:
        name = str(sale)
        sale.delete()
        messages.success(request, _t(request, "Flash sale {name} deleted.").format(name=name))
    return redirect("pystore_admin:flash_sale_list")
