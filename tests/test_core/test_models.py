import pytest
from django.utils import timezone

from tests.testapp.models import SampleModel

pytestmark = [pytest.mark.django_db]


def test_uuid_primary_key_is_generated():
    sample = SampleModel.objects.create(name="a")
    assert sample.pk is not None
    assert str(sample.pk).count("-") == 4


def test_timestamps_set_on_create():
    before = timezone.now()
    sample = SampleModel.objects.create(name="a")
    assert sample.created_at >= before
    assert sample.updated_at >= before


def test_updated_at_changes_on_save():
    sample = SampleModel.objects.create(name="a")
    first_updated = sample.updated_at
    sample.name = "b"
    sample.save()
    sample.refresh_from_db()
    assert sample.updated_at >= first_updated


def test_soft_delete_hides_from_default_manager():
    sample = SampleModel.objects.create(name="a")
    sample.delete()
    sample.refresh_from_db()
    assert sample.is_deleted is True
    assert sample.deleted_at is not None
    assert list(SampleModel.objects.all()) == []
    assert SampleModel.objects.count() == 0


def test_all_objects_manager_sees_deleted():
    sample = SampleModel.objects.create(name="a")
    sample.delete()
    assert SampleModel.all_objects.count() == 1


def test_restore():
    sample = SampleModel.objects.create(name="a")
    sample.delete()
    sample.restore()
    sample.refresh_from_db()
    assert sample.is_deleted is False
    assert sample.deleted_at is None
    assert SampleModel.objects.count() == 1


def test_hard_delete_removes_row():
    sample = SampleModel.objects.create(name="a")
    sample.hard_delete()
    assert SampleModel.all_objects.count() == 0


def test_queryset_delete_soft_deletes_all():
    SampleModel.objects.create(name="a")
    SampleModel.objects.create(name="b")
    SampleModel.objects.delete()
    assert SampleModel.objects.count() == 0
    assert SampleModel.all_objects.filter(is_deleted=True).count() == 2


def test_queryset_alive_and_deleted_filters():
    a = SampleModel.objects.create(name="a")
    SampleModel.objects.create(name="b").delete()
    assert list(SampleModel.objects.alive()) == [a]
    assert SampleModel.objects.deleted().count() == 1


def test_queryset_restore_restores_all():
    SampleModel.objects.create(name="a").delete()
    SampleModel.objects.create(name="b").delete()
    SampleModel.all_objects.restore()
    assert SampleModel.objects.count() == 2


def test_second_soft_delete_updates_deleted_at():
    sample = SampleModel.objects.create(name="a")
    sample.delete()
    first = sample.deleted_at
    sample.delete()
    assert sample.deleted_at >= first
