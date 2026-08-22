from __future__ import annotations

import asyncio
import json
import os
import uuid
from datetime import datetime
import pandas as pd
from fastapi import APIRouter, BackgroundTasks, File, HTTPException, Request, UploadFile, Query
from fastapi.responses import FileResponse, StreamingResponse
import redis.asyncio as aioredis

from jobs.manager import JobManager
from jobs.events import JobEventPublisher
from jobs.models import Job, JobStatus
from workers.celery_app import celery_app
from workers.tasks import process_job_task
from pipeline.runner import run_job

router = APIRouter(prefix="/api/jobs", tags=["jobs"])

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6380/0")
UPLOADS_DIR = os.getenv("UPLOADS_DIR", "uploads")
OUTPUTS_DIR = os.getenv("OUTPUTS_DIR", "outputs")

os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(OUTPUTS_DIR, exist_ok=True)


def run_job_background_fallback(job_id: str, input_path: str, output_path: str):
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
                product_concurrency=2,
            )
        )

        job = manager.get_job(job_id)
        if job:
            job.status = JobStatus.COMPLETED if job_result.error is None else JobStatus.FAILED
            job.completed_at = datetime.utcnow()
            job.completed = job_result.processed
            job.successful = job_result.successful
            job.warnings = job_result.warnings
            job.failed = job_result.failed
            job.output_path = job_result.output_path
            job.error = job_result.error
            manager.save_job(job)
    except Exception as exc:
        err = f"{type(exc).__name__}: {exc}"
        job = manager.get_job(job_id)
        if job:
            job.status = JobStatus.FAILED
            job.completed_at = datetime.utcnow()
            job.error = err
            manager.save_job(job)
    finally:
        manager.close()


@router.post("", response_model=dict)
async def create_job(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported.")

    job_id = uuid.uuid4().hex[:10]
    input_filename = f"{job_id}_{file.filename}"
    input_path = os.path.join(UPLOADS_DIR, input_filename)
    output_path = os.path.join(OUTPUTS_DIR, f"{job_id}_enriched.csv")

    content = await file.read()
    with open(input_path, "wb") as f:
        f.write(content)

    # Determine product count from CSV
    try:
        df = pd.read_csv(input_path)
        total_products = len(df)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid CSV file: {exc}")

    manager = JobManager()
    job = manager.create_job(job_id, file.filename, total_products)
    job.output_path = output_path
    manager.save_job(job)
    manager.close()

    # Check if Celery worker is active
    worker_active = False
    try:
        insp = celery_app.control.inspect(timeout=0.5)
        pings = insp.ping()
        if pings:
            worker_active = True
    except Exception:
        worker_active = False

    if worker_active:
        process_job_task.delay(
            job_id=job_id,
            input_path=input_path,
            output_path=output_path,
            product_concurrency=2,
        )
    else:
        # Fallback to in-process FastAPI background task execution
        background_tasks.add_task(
            run_job_background_fallback,
            job_id,
            input_path,
            output_path,
        )

    return {
        "job_id": job_id,
        "status": job.status.value,
        "total": total_products,
    }


@router.get("/{job_id}", response_model=Job)
async def get_job(job_id: str):
    manager = JobManager()
    job = manager.get_job(job_id)
    manager.close()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/{job_id}/events")
async def get_job_events(
    job_id: str,
    request: Request,
    last_event_id: str | None = Query(None),
):
    stream_key = f"job:{job_id}:events"
    client_last_id = (
        request.headers.get("Last-Event-ID") or last_event_id or "0-0"
    )

    async def event_generator():
        r = aioredis.from_url(REDIS_URL, decode_responses=True)
        current_id = client_last_id

        try:
            while True:
                if await request.is_disconnected():
                    break

                entries = await r.xread({stream_key: current_id}, count=20, block=2000)
                if not entries:
                    yield ": ping\n\n"
                    continue

                for _, stream_events in entries:
                    for event_id, fields in stream_events:
                        current_id = event_id
                        raw_data = fields.get("data", "{}")
                        try:
                            data_obj = json.loads(raw_data)
                            event_type = data_obj.get("type", "message")
                        except Exception:
                            event_type = "message"

                        yield f"id: {event_id}\nevent: {event_type}\ndata: {raw_data}\n\n"

                        if event_type in ("job.completed", "job.failed"):
                            return
        finally:
            await r.close()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/{job_id}/download")
async def download_job_output(job_id: str):
    manager = JobManager()
    job = manager.get_job(job_id)
    manager.close()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if not job.output_path or not os.path.exists(job.output_path):
        raise HTTPException(status_code=404, detail="Output file not ready or not found")

    download_name = f"enriched_{job.filename}"
    return FileResponse(
        path=job.output_path,
        media_type="text/csv",
        filename=download_name,
    )


@router.post("/{job_id}/cancel", response_model=dict)
async def cancel_job(job_id: str):
    manager = JobManager()
    job = manager.get_job(job_id)
    if not job:
        manager.close()
        raise HTTPException(status_code=404, detail="Job not found")

    job.status = JobStatus.CANCELLED
    job.error = "Cancelled by user"
    manager.save_job(job)
    manager.close()

    publisher = JobEventPublisher()
    await publisher.publish(
        job_id,
        {
            "type": "job.failed",
            "job_id": job_id,
            "error": "Job cancelled by user",
        },
    )
    await publisher.close()

    return {"job_id": job_id, "status": "cancelled"}

