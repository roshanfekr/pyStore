from django.conf import settings

from config.celery import app as celery_app


def test_celery_app_main():
    assert celery_app.main == "pystore"


def test_celery_uses_json_serialization():
    assert settings.CELERY_TASK_SERIALIZER == "json"
    assert settings.CELERY_RESULT_SERIALIZER == "json"
    assert "json" in settings.CELERY_ACCEPT_CONTENT


def test_celery_tasks_run_eagerly_in_tests():
    assert settings.CELERY_TASK_ALWAYS_EAGER is True
