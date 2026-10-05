import pytest

from core.infrastructure import DependencyContainer, atomic, container, run_in_transaction
from tests.testapp.models import SampleModel


class ServiceStub:
    pass


def test_resolve_returns_new_instance_per_call():
    box = DependencyContainer()
    box.register("service", ServiceStub)
    first = box.resolve("service")
    second = box.resolve("service")
    assert isinstance(first, ServiceStub)
    assert first is not second


def test_singleton_returns_same_instance():
    box = DependencyContainer()
    box.register("service", ServiceStub, singleton=True)
    assert box.resolve("service") is box.resolve("service")


def test_register_instance_always_returns_same():
    box = DependencyContainer()
    stub = ServiceStub()
    box.register_instance("service", stub)
    assert box.resolve("service") is stub


def test_resolve_unregistered_raises():
    box = DependencyContainer()
    with pytest.raises(KeyError):
        box.resolve("missing")


def test_override_replaces_factory():
    box = DependencyContainer()
    box.register("service", ServiceStub, singleton=True)
    replacement = ServiceStub()
    box.override("service", lambda: replacement)
    assert box.resolve("service") is replacement


def test_global_container_is_usable():
    container.register("service", ServiceStub)
    try:
        assert isinstance(container.resolve("service"), ServiceStub)
    finally:
        container.clear()


@pytest.mark.django_db
def test_run_in_transaction_commits():
    run_in_transaction(SampleModel.objects.create, name="a")
    assert SampleModel.objects.filter(name="a").exists()


@pytest.mark.django_db
def test_run_in_transaction_rolls_back_on_error():
    def failing():
        SampleModel.objects.create(name="rollback")
        raise RuntimeError("fail")

    with pytest.raises(RuntimeError):
        run_in_transaction(failing)
    assert SampleModel.objects.filter(name="rollback").exists() is False


@pytest.mark.django_db
def test_atomic_context_rolls_back():
    with pytest.raises(RuntimeError):
        with atomic():
            SampleModel.objects.create(name="x")
            raise RuntimeError("fail")
    assert SampleModel.objects.filter(name="x").exists() is False
