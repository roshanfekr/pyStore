from django.db import models

from core.models import BaseModel


class SampleModel(BaseModel):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name
