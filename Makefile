.PHONY: dev docker test lint format clean

# Start local FastAPI dev server with reloading enabled
dev:
	@echo "Starting FastAPI local development server..."
	PYTHONPATH=. .venv/bin/uvicorn backend.api.main:app --reload --host 127.0.0.1 --port 8000

# Build and start containerized services (DB, Qdrant, Backend)
docker:
	@echo "Building and launching containerized services..."
	docker compose up --build -d

# Run Python integration tests
test:
	@echo "Running backend integration tests..."
	PYTHONPATH=. .venv/bin/python3 backend/scripts/test_pipeline_full.py

# Run linters for both backend (Ruff) and frontend (Oxlint)
lint:
	@echo "Running backend linting (Ruff)..."
	.venv/bin/ruff check backend/
	@echo "Running frontend linting (Oxlint)..."
	npm --prefix frontend run lint

# Run formatters for backend (Black and Ruff isort)
format:
	@echo "Formatting Python code with Black..."
	.venv/bin/black backend/
	@echo "Sorting imports with Ruff..."
	.venv/bin/ruff check --select I --fix backend/

# Clean cache and temporary build directories
clean:
	@echo "Cleaning cache files..."
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache
	rm -rf frontend/dist
	rm -rf backend/data/qdrant
