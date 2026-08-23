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

# Install python dependencies (using standard pip to ensure bins are in PATH)
RUN cd backend && pip install --no-cache-dir .

# Copy backend source code
COPY backend/ ./backend/

# Copy compiled frontend from Stage 1
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Install a simple static server for the frontend
RUN npm install -g serve

# Copy the startup script
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Environment variables
ENV PYTHONPATH=/app/backend/src
ENV REDIS_URL=redis://localhost:6379/0

# Expose port for FastAPI
EXPOSE 8000

# Run the startup script
CMD ["/app/start.sh"]
