# ==========================================
# Build the Python Backend + Redis
# ==========================================
FROM python:3.11-slim

WORKDIR /app

# Install Redis Server and build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    redis-server \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy backend definitions and install
COPY backend/pyproject.toml ./backend/
RUN cd backend && pip install --no-cache-dir .

# Copy backend source code
COPY backend/ ./backend/

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
