from typing import Generic, TypeVar

from django.db import models

from core.exceptions import NotFoundError

ModelT = TypeVar("ModelT", bound=models.Model)


class BaseRepository(Generic[ModelT]):
    model: type[ModelT]

    def __init__(self, model: type[ModelT] | None = None):
        if model is not None:
            self.model = model

    def get_queryset(self) -> models.QuerySet:
        return self.model.objects.all()

    def get(self, pk) -> ModelT:
        try:
            return self.get_queryset().get(pk=pk)
        except self.model.DoesNotExist:
            raise NotFoundError(
                f"{self.model.__name__} not found", code=f"{self.model._meta.label_lower}.not_found"
            ) from None

    def list(self, *, filters: dict | None = None, ordering: list[str] | None = None) -> models.QuerySet:
        queryset = self.get_queryset()
        if filters:
            queryset = queryset.filter(**filters)
        if ordering:
            queryset = queryset.order_by(*ordering)
        return queryset

    def create(self, **data) -> ModelT:
        return self.model.objects.create(**data)

    def update(self, instance: ModelT, **data) -> ModelT:
        for field, value in data.items():
            setattr(instance, field, value)
        instance.save()
        return instance

    def delete(self, instance: ModelT) -> None:
        instance.delete()

    def hard_delete(self, instance: ModelT) -> None:
        instance.hard_delete()

    def exists(self, **filters) -> bool:
        return self.get_queryset().filter(**filters).exists()

    def count(self, *, filters: dict | None = None) -> int:
        return self.list(filters=filters).count()
