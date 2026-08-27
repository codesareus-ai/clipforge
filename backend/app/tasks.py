"""Celery worker (optional). Enable with CELERY_ENABLED=true and run:
    celery -A app.tasks.celery worker --loglevel=info
Otherwise the API uses FastAPI BackgroundTasks (see app/routes.py).
Heavy deps (torch, faster-whisper) are imported lazily inside the task body,
so importing this module is cheap and never fails on missing optional deps.
"""
from __future__ import annotations

import os

from app.config import get_settings

settings = get_settings()
CELERY_ENABLED = os.getenv("CELERY_ENABLED", "false").lower() == "true"


if CELERY_ENABLED:
    from celery import Celery

    celery = Celery("clipforge", broker=settings.REDIS_URL, backend=settings.REDIS_URL)

    @celery.task(name="execute_pipeline")
    def execute_pipeline(job_id: str, body: dict):
        from app.worker import execute_pipeline as run

        run(job_id, body)
else:
    celery = None
