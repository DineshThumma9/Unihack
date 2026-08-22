from __future__ import annotations

import os
from celery import Celery

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6380/0")
REDIS_RESULT_URL = os.getenv("REDIS_RESULT_URL", os.getenv("REDIS_URL", "redis://localhost:6380/1"))

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
