import logging

import pytest
from django.conf import settings as django_settings

from core.jobs import job_task

pytestmark = [pytest.mark.django_db]


@job_task(max_retries=2)
def successful_job(self, value):
    return value * 2


@job_task(autoretry_for=(), max_retries=0)
def failing_job(self):
    raise RuntimeError("job failed on purpose")


@job_task(max_retries=3)
def retrying_job(self):
    raise RuntimeError("always fails")


def test_job_runs_with_logging_and_result(caplog):
    with caplog.at_level(logging.INFO, logger="core.jobs"):
        result = successful_job.delay(21)
        assert result.get() == 42
    assert "started" in caplog.text
    assert "succeeded" in caplog.text


def test_job_failure_propagates():
    with pytest.raises(RuntimeError, match="job failed on purpose"):
        failing_job.delay()


def test_on_failure_hook_logs_error(caplog):
    exc = RuntimeError("boom")

    with caplog.at_level(logging.ERROR, logger="core.jobs"):
        failing_job.on_failure(exc, "task-id-1", (), {}, None)

    assert "failed" in caplog.text
    assert "boom" in caplog.text


def test_job_has_retry_configuration():
    assert retrying_job.max_retries == 3


def test_beat_schedule_is_configurable():
    assert hasattr(django_settings, "CELERY_BEAT_SCHEDULE")
    assert django_settings.CELERY_BEAT_SCHEDULE == {}
