.PHONY: dev docker test lint clean

# Default target
all: dev

# Start local FastAPI dev server with reloading enabled
dev:
	@echo "Starting FastAPI local development server..."
	PYTHONPATH=. .venv/bin/uvicorn backend.api.main:app --reload --host 127.0.0.1 --port 8000

# Build and start containerized backend
docker:
	@echo "Building and launching containerized backend..."
	docker compose up --build -d

# Run Python integration tests
test:
	@echo "Running backend integration tests..."
	PYTHONPATH=. .venv/bin/python3 backend/scripts/test_pipeline_full.py

# Run linters
lint:
	@echo "Running frontend linting..."
	npm --prefix frontend run lint

# Clean cache directories
clean:
	@echo "Cleaning cache files..."
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache
