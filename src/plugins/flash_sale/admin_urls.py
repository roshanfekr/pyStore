
from django.urls import path

from plugins.flash_sale import admin_views

admin_urlpatterns = [
    path("flash-sale/", admin_views.sale_list_view, name="flash_sale_list"),
    path("flash-sale/add/", admin_views.sale_edit_view, name="flash_sale_add"),
    path("flash-sale/<uuid:sale_id>/edit/", admin_views.sale_edit_view, name="flash_sale_edit"),
    path("flash-sale/<uuid:sale_id>/delete/", admin_views.sale_delete_view, name="flash_sale_delete"),
]
