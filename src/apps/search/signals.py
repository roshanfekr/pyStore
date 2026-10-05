from django.db.models.signals import post_save

from apps.catalog.models import Product


def connect_signals():
    post_save.connect(product_saved_handler, sender=Product)


def product_saved_handler(sender, instance, **kwargs):
    from apps.search.tasks import index_product_task

    index_product_task.delay(str(instance.pk))
