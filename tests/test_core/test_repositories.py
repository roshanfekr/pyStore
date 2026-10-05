import pytest

from core.exceptions import NotFoundError
from core.repositories import BaseRepository
from tests.testapp.models import SampleModel

pytestmark = [pytest.mark.django_db]


class SampleRepository(BaseRepository):
    model = SampleModel


def test_create_persists():
    repo = SampleRepository()
    sample = repo.create(name="a")
    assert SampleModel.objects.filter(pk=sample.pk, name="a").exists()


def test_get_returns_instance():
    repo = SampleRepository()
    sample = repo.create(name="a")
    assert repo.get(sample.pk).name == "a"


def test_get_missing_raises_not_found():
    repo = SampleRepository()
    with pytest.raises(NotFoundError):
        repo.get("00000000-0000-0000-0000-000000000000")


def test_soft_deleted_item_not_returned():
    repo = SampleRepository()
    sample = repo.create(name="a")
    repo.delete(sample)
    with pytest.raises(NotFoundError):
        repo.get(sample.pk)


def test_list_with_filters_and_ordering():
    repo = SampleRepository()
    repo.create(name="b")
    repo.create(name="a")
    repo.create(name="c")

    names = [s.name for s in repo.list(ordering=["name"])]
    assert names == ["a", "b", "c"]

    filtered = repo.list(filters={"name": "a"})
    assert filtered.count() == 1


def test_update_changes_fields():
    repo = SampleRepository()
    sample = repo.create(name="a")
    updated = repo.update(sample, name="z")
    assert updated.name == "z"
    sample.refresh_from_db()
    assert sample.name == "z"


def test_delete_is_soft_and_hard_delete_removes():
    repo = SampleRepository()
    sample = repo.create(name="a")
    repo.delete(sample)
    assert SampleModel.all_objects.filter(pk=sample.pk, is_deleted=True).exists()
    repo.hard_delete(sample)
    assert SampleModel.all_objects.filter(pk=sample.pk).exists() is False


def test_exists_and_count():
    repo = SampleRepository()
    repo.create(name="a")
    repo.create(name="a")
    repo.create(name="b")
    assert repo.exists(name="a") is True
    assert repo.exists(name="x") is False
    assert repo.count(filters={"name": "a"}) == 2
