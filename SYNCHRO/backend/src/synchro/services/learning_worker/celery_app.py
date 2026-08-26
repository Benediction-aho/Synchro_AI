"""Celery app configuration for SYNCHRO background workers."""

from celery import Celery
from celery.schedules import crontab

from synchro.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "synchro",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "synchro.services.learning_worker.tasks",
        "synchro.services.evolution_worker.tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,
    worker_prefetch_multiplier=4,
    beat_schedule={
        "nightly-learning-job": {
            "task": "synchro.services.learning_worker.tasks.nightly_learning_job",
            "schedule": crontab(hour=2, minute=0),  # 02:00 UTC
        },
        "evolution-cycle": {
            "task": "synchro.services.evolution_worker.tasks.run_evolution_cycle",
            "schedule": crontab(hour=4, minute=0),  # 04:00 UTC (after learning)
        },
    },
)

# Make sure tasks are registered when module is imported
celery_app.autodiscover_tasks(["synchro.services.learning_worker", "synchro.services.evolution_worker"])