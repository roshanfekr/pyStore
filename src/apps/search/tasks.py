from apps.catalog.models import Product
from apps.search.service import search_service
from core.jobs import job_task


@job_task(autoretry_for=(), max_retries=0)
def index_product_task(self, product_id: str):
    from django.core.exceptions import ObjectDoesNotExist

    try:
        product = Product.objects.get(pk=product_id)
    except (ObjectDoesNotExist, ValueError):
        search_service.remove_product(product_id)
        return False
    search_service.index_product(product)
    return True


@job_task(autoretry_for=(), max_retries=0)
def reindex_search_task(self):
    return search_service.reindex_all()
