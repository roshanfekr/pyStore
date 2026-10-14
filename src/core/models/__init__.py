from core.models.base import IntegerPKModel, TimeStampedModel
from core.models.soft_delete import (
    AllObjectsManager,
    SoftDeleteManager,
    SoftDeleteModel,
    SoftDeleteQuerySet,
)
from core.plugins.models import PluginState
from core.settings.models import Setting


class BaseModel(IntegerPKModel, TimeStampedModel, SoftDeleteModel):
    class Meta:
        abstract = True


__all__ = [
    "AllObjectsManager",
    "BaseModel",
    "IntegerPKModel",
    "PluginState",
    "Setting",
    "SoftDeleteManager",
    "SoftDeleteModel",
    "SoftDeleteQuerySet",
    "TimeStampedModel",
]
