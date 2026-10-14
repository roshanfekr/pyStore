from django.db import models


class IntegerPKModel(models.Model):
    """Abstract base that gives every model an auto-incrementing integer PK.

    Django's implicit ``BigAutoField`` is declared explicitly here so the
    intent is obvious and so all entities share the same primary key type.
    """

    id = models.BigAutoField(primary_key=True, auto_created=True, serialize=False, verbose_name="ID")

    class Meta:
        abstract = True


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
