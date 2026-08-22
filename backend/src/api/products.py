from __future__ import annotations

from fastapi import APIRouter, HTTPException
from jobs.manager import JobManager
from jobs.models import ProductRunResult

router = APIRouter(prefix="/api/jobs", tags=["products"])


@router.get("/{job_id}/products", response_model=list[ProductRunResult])
async def list_product_details(job_id: str):
    manager = JobManager()
    job = manager.get_job(job_id)
    if not job:
        manager.close()
        raise HTTPException(status_code=404, detail="Job not found")

    results = manager.get_all_product_results(job_id, job.total)
    manager.close()
    return results


@router.get("/{job_id}/products/{index}", response_model=ProductRunResult)
async def get_product_detail(job_id: str, index: int):
    manager = JobManager()
    result = manager.get_product_result(job_id, index)
    manager.close()

    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"Product detail for index {index} in job {job_id} not found",
        )
    return result
