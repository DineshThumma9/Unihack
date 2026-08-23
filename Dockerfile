# ==========================================
# STAGE 1: Build the React Frontend
# ==========================================
FROM node:20-slim AS frontend-builder

WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install

COPY frontend/ .
RUN npm run build

# ==========================================
# STAGE 2: Build the Python Backend + Redis
# ==========================================
FROM python:3.11-slim

WORKDIR /app

# Install Redis Server, Node (for simple frontend serving), and build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    redis-server \
    nodejs \
    npm \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast python package management
RUN pip install --no-cache-dir uv

# Copy python project definition
COPY backend/pyproject.toml backend/uv.lock ./backend/

# Install python dependencies
RUN cd backend && /bin/bash -c "uv sync --frozen || uv pip install --system -r <(uv export) || pip install --no-cache-dir fastapi uvicorn celery redis pandas langchain langchain-mistralai langgraph python-dotenv python-multipart"

# Copy backend source code
COPY backend/ ./backend/

# Copy compiled frontend from Stage 1
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Install a simple static server for the frontend
RUN npm install -g serve

# Create the startup script
RUN echo '#!/bin/bash\n\
# 1. Start Redis in the background\n\
redis-server --daemonize yes\n\
\n\
# 2. Start Celery worker in the background\n\
cd /app/backend/src && celery -A workers.celery_worker worker --loglevel=info &\n\
\n\
# 3. Start the Frontend static server in the background\n\
serve -s /app/frontend/dist -l 5173 &\n\
\n\
# 4. Start the FastAPI backend in the foreground\n\
cd /app/backend/src && uvicorn app:app --host 0.0.0.0 --port 8000\n\
' > /app/start.sh

RUN chmod +x /app/start.sh

# Environment variables
ENV PYTHONPATH=/app/backend/src
ENV REDIS_URL=redis://localhost:6379/0

# Expose ports for both Frontend and Backend
EXPOSE 8000 5173

# Run the startup script
CMD ["/app/start.sh"]
