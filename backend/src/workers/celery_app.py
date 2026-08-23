from __future__ import annotations

from celery import Celery
from config import settings

REDIS_URL = settings.REDIS_URL
REDIS_RESULT_URL = settings.REDIS_URL

celery_app = Celery(
    "product_enrichment_tasks",
    broker=REDIS_URL,
    backend=REDIS_RESULT_URL,
    include=["workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)
