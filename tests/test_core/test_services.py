from core.events import DomainEvent
from core.exceptions import BusinessRuleError, UnexpectedError
from core.services import BaseService, Result


class Greeted(DomainEvent):
    pass


class GreetService(BaseService):
    def execute(self, name):
        if name == "boom":
            raise BusinessRuleError("no greetings for boom")
        if name == "crash":
            raise ValueError("unexpected")
        self.raise_event(Greeted())
        return f"hello {name}"


def test_run_returns_ok_result_with_value():
    result = GreetService().run("ali")
    assert result.success is True
    assert bool(result) is True
    assert result.value == "hello ali"
    assert result.error is None


def test_run_catches_application_error():
    result = GreetService().run("boom")
    assert result.success is False
    assert bool(result) is False
    assert result.value is None
    assert isinstance(result.error, BusinessRuleError)
    assert result.error.code == "business_rule_violation"


def test_run_wraps_unexpected_exception():
    result = GreetService().run("crash")
    assert result.success is False
    assert isinstance(result.error, UnexpectedError)
    assert result.error.status_code == 500


def test_raise_event_and_collect_clears_queue():
    service = GreetService()
    service.run("ali")
    service.run("reza")

    events = service.collect_events()
    assert len(events) == 2
    assert all(isinstance(event, Greeted) for event in events)
    assert service.collect_events() == []


def test_result_ok_and_error_factories():
    ok = Result.ok(42)
    err = Result.fail(BusinessRuleError("bad"))

    assert ok.value == 42
    assert err.error.code == "business_rule_violation"
    assert err.error.message == "bad"
