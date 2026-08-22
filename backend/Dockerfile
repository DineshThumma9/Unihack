FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install --no-cache-dir uv

# Copy project definition and lock file
COPY pyproject.toml uv.lock ./

# Install python dependencies
RUN uv sync --frozen || uv pip install --system -r <(uv export) || pip install --no-cache-dir fastapi uvicorn celery redis pandas langchain langchain-mistralai langgraph python-dotenv python-multipart

# Copy backend source code
COPY . .

# Set PYTHONPATH
ENV PYTHONPATH=/app/src
ENV REDIS_URL=redis://redis:6379/0

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
