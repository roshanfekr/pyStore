import logging

from celery import Task, shared_task

logger = logging.getLogger("core.jobs")


class JobTask(Task):
    def before_start(self, task_id, args, kwargs):
        logger.info("Task %s[%s] started", self.name, task_id)

    def on_success(self, retval, task_id, args, kwargs):
        logger.info("Task %s[%s] succeeded", self.name, task_id)

    def on_retry(self, exc, task_id, args, kwargs, einfo):
        logger.warning("Task %s[%s] retry: %s", self.name, task_id, exc)

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.error("Task %s[%s] failed: %s", self.name, task_id, exc)


def job_task(func=None, *, max_retries: int = 3, autoretry_for=(Exception,), **options):
    def decorator(fn):
        return shared_task(
            base=JobTask,
            bind=True,
            autoretry_for=autoretry_for,
            retry_kwargs={"max_retries": max_retries},
            retry_backoff=True,
            **options,
        )(fn)

    if func is not None:
        return decorator(func)
    return decorator
