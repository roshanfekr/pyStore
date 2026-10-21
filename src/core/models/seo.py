from django.db import models


class SEOMixin(models.Model):
    """Shared SEO metadata fields for content models.

    Lives in the core kernel so that content models in different bounded
    modules (for example CMS pages and catalog brands) share one definition
    instead of duplicating the fields.
    """

    meta_title = models.CharField(max_length=200, blank=True)
    meta_description = models.CharField(max_length=300, blank=True)
    canonical_url = models.CharField(max_length=500, blank=True)
    robots_meta = models.CharField(max_length=100, default="index, follow")
    og_title = models.CharField(max_length=200, blank=True)
    og_description = models.CharField(max_length=300, blank=True)
    structured_data = models.JSONField(default=dict, blank=True)

    class Meta:
        abstract = True
