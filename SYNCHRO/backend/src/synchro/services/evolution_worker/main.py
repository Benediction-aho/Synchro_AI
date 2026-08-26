"""Evolution Worker runnable entrypoint."""

from synchro.services.learning_worker.celery_app import celery_app

if __name__ == "__main__":
    celery_app.worker_main(["worker", "--loglevel=INFO"])