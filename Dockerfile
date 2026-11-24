# Use official slim Python runtime
FROM python:3.12-slim

# Prevent Python from writing .pyc files and buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install uv for fast, reliable package management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install dependencies using uv
COPY requirements.txt .
RUN uv pip install --system --no-cache -r requirements.txt

# Copy application source code, data, prompts, and frontend
COPY app/ ./app/
COPY data/ ./data/
COPY prompts/ ./prompts/
COPY frontend/ ./frontend/

# Create cache directories
RUN mkdir -p cache/webhook_raw cache/call_summaries

# Default port (Render provides $PORT at runtime)
ENV PORT=8000
EXPOSE 8000

# Start FastAPI webhook server with Uvicorn
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
