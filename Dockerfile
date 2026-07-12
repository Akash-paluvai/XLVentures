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
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Create backend data directories and ensure correct permissions
RUN mkdir -p backend/data && chmod -R 775 backend/data

# Create and switch to a secure non-root user with home directory and cache folders
RUN useradd -m -s /bin/bash -u 10001 appuser \
    && mkdir -p /home/appuser/.cache/huggingface \
    && mkdir -p /home/appuser/.cache/sentence_transformers \
    && chown -R appuser:appuser /home/appuser /app

# Configure HuggingFace cache folders to be under the writable home directory
ENV HOME=/home/appuser
ENV HF_HOME=/home/appuser/.cache/huggingface
ENV TRANSFORMERS_CACHE=/home/appuser/.cache/huggingface
ENV SENTENCE_TRANSFORMERS_HOME=/home/appuser/.cache/sentence_transformers

USER appuser

# Pre-download SentenceTransformer weights so they are cached inside the image and startup is instant
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"

EXPOSE 8000

# Healthcheck to verify FastAPI backend is healthy
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Start the application
CMD ["sh", "-c", "uvicorn backend.api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
