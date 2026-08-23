#!/bin/bash
# 1. Start Redis in the background
redis-server --daemonize yes

# 2. Start Celery worker in the background
cd /app/backend/src && celery -A workers.celery_app worker -c 2 --loglevel=info &

# 3. Start the FastAPI backend (which also serves the frontend UI)
cd /app/backend/src && uvicorn app:app --host 0.0.0.0 --port "${PORT:-8000}"