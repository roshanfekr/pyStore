from core.models.base import TimeStampedModel, UUIDModel
from core.models.soft_delete import (
    AllObjectsManager,
    SoftDeleteManager,
    SoftDeleteModel,
    SoftDeleteQuerySet,
)
from core.plugins.models import PluginState
from core.settings.models import Setting


class BaseModel(UUIDModel, TimeStampedModel, SoftDeleteModel):
    class Meta:
        abstract = True


__all__ = [
    "AllObjectsManager",
    "BaseModel",
    "PluginState",
    "Setting",
    "SoftDeleteManager",
    "SoftDeleteModel",
    "SoftDeleteQuerySet",
    "TimeStampedModel",
    "UUIDModel",
]
