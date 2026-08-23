from __future__ import annotations

import sys
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Ensure src directory is in python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api.jobs import router as jobs_router
from api.products import router as products_router
from config import settings

app = FastAPI(
    title="CSV Product Enrichment API",
    version="1.0.0",
    description="Backend API for CSV Product Intelligence Pipeline",
)

# Handle multiple comma-separated URLs and strip trailing slashes
allowed_origins = [url.strip().rstrip("/") for url in settings.FRONTEND_URL.split(",") if url.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins if allowed_origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(jobs_router)
app.include_router(products_router)


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "CSV Product Enrichment API"}

