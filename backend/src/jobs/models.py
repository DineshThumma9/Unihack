from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal, Any
from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Job(BaseModel):
    id: str
    filename: str
    status: JobStatus = JobStatus.QUEUED

    total: int = 0
    completed: int = 0
    successful: int = 0
    warnings: int = 0
    failed: int = 0

    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: datetime | None = None
    completed_at: datetime | None = None

    output_path: str | None = None
    error: str | None = None


class JobResult(BaseModel):
    job_id: str
    total: int
    processed: int
    successful: int
    warnings: int
    failed: int
    output_path: str | None = None
    error: str | None = None


class ProductRunResult(BaseModel):
    index: int
    mpn: str

    status: Literal["success", "warning", "failed"]

    validation: dict[str, bool] = Field(default_factory=dict)
    validation_score: float = 0.0

    manufacturer: str | None = None
    brand: str | None = None

    attributes_found: int = 0

    processing_time: float = 0.0

    needs_review: bool = False

    error: str | None = None

    delivery_row: dict[str, Any] | None = None
    source_map: dict[str, str] | None = None
