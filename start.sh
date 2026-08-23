#!/bin/bash
# 1. Start Redis in the background
redis-server --daemonize yes

# 2. Start Celery worker in the background
cd /app/backend/src && celery -A workers.celery_worker worker --loglevel=info &

# 3. Start the FastAPI backend (which also serves the frontend UI)
cd /app/backend/src && uvicorn app:app --host 0.0.0.0 --port 8000