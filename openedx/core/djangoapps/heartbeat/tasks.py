"""
A trivial task for health checks
"""
from celery.task import task


@task(routing_key=settings.HIGH_PRIORITY_QUEUE)
def sample_task():
    return True
