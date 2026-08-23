from __future__ import annotations

import asyncio
from datetime import datetime

from workers.celery_app import celery_app
from jobs.manager import JobManager
from jobs.events import JobEventPublisher
from jobs.models import JobStatus
from pipeline.runner import run_job


@celery_app.task(name="tasks.process_job", bind=True)
def process_job_task(
    self,
    job_id: str,
    input_path: str,
    output_path: str,
    product_concurrency: int = 2,
    limit: int | None = None,
):
    manager = JobManager()
    publisher = JobEventPublisher()

    job = manager.get_job(job_id)
    if job:
        job.status = JobStatus.RUNNING
        job.started_at = datetime.utcnow()
        manager.save_job(job)

    try:
        job_result = asyncio.run(
            run_job(
                job_id=job_id,
                input_path=input_path,
                output_path=output_path,
                event_publisher=publisher,
                job_manager=manager,
                product_concurrency=product_concurrency,
                limit=limit,
            )
        )

        job = manager.get_job(job_id)
        if job:
            if job.status != JobStatus.CANCELLED:
                job.status = JobStatus.COMPLETED if job_result.error is None else JobStatus.FAILED
            job.completed_at = datetime.utcnow()
            job.completed = job_result.processed
            job.successful = job_result.successful
            job.warnings = job_result.warnings
            job.failed = job_result.failed
            job.output_path = job_result.output_path
            if job.status != JobStatus.CANCELLED:
                job.error = job_result.error
            manager.save_job(job)

        return job_result.model_dump()
    except Exception as exc:
        err = f"{type(exc).__name__}: {exc}"
        job = manager.get_job(job_id)
        if job:
            job.status = JobStatus.FAILED
            job.completed_at = datetime.utcnow()
            job.error = err
            manager.save_job(job)
        raise exc
    finally:
        manager.close()
