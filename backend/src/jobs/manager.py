from __future__ import annotations

import json
import os
from typing import Any
import redis
from jobs.models import Job, JobStatus, ProductRunResult

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6380/0")


class JobManager:
    def __init__(self, redis_url: str | None = None):
        self.redis_url = redis_url or REDIS_URL
        self._r = redis.Redis.from_url(self.redis_url, decode_responses=True)

    def create_job(self, job_id: str, filename: str, total: int) -> Job:
        job = Job(
            id=job_id,
            filename=filename,
            status=JobStatus.QUEUED,
            total=total,
        )
        self.save_job(job)
        return job

    def save_job(self, job: Job) -> None:
        key = f"job:{job.id}:meta"
        self._r.set(key, job.model_dump_json())

    def get_job(self, job_id: str) -> Job | None:
        key = f"job:{job_id}:meta"
        raw = self._r.get(key)
        if not raw:
            return None
        return Job.model_validate_json(raw)

    def save_product_result(self, job_id: str, res: ProductRunResult) -> None:
        key = f"job:{job_id}:product:{res.index}"
        self._r.set(key, res.model_dump_json())

    def get_product_result(self, job_id: str, index: int) -> ProductRunResult | None:
        key = f"job:{job_id}:product:{index}"
        raw = self._r.get(key)
        if not raw:
            return None
        return ProductRunResult.model_validate_json(raw)

    def get_all_product_results(self, job_id: str, total: int) -> list[ProductRunResult]:
        results = []
        for index in range(total):
            res = self.get_product_result(job_id, index)
            if res:
                results.append(res)
        return results

    def close(self):
        self._r.close()
