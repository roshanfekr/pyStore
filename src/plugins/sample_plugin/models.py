from django.db import models

from core.models import BaseModel


class SampleData(BaseModel):
    message = models.CharField(max_length=255)

    def __str__(self):
        return self.message
