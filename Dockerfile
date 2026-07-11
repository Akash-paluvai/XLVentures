FROM python:3.11-slim

# Prevent Python from writing .pyc files and buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install curl for healthchecks
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Create backend data directories and ensure correct permissions
RUN mkdir -p backend/data && chmod -R 775 backend/data

# Create and switch to a secure non-root user
RUN useradd -u 10001 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Healthcheck to verify FastAPI backend is healthy
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Start the application
CMD ["sh", "-c", "uvicorn backend.api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
