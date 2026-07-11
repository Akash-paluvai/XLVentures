# ADR 002: Why FastAPI

## Context & Problem
The backend service serves as the core coordinator between frontend React views and backend AI agents. We need an API layer that:
1. Supports async/non-blocking operations (LLM API calls can take seconds to complete).
2. Generates clean self-documenting APIs (OpenAPI/Swagger) for easy testing.
3. Incorporates lightweight middlewares for response-time measurement and request tracking.

## Decision
We select **FastAPI** as the backend web framework.

## Consequences & Rationale
* **Async Concurrency**: FastAPI is built on top of Starlette and Uvicorn, offering native `async/await` handling. This allows the backend to handle high volumes of concurrent requests while waiting for external LLM API endpoints.
* **Auto OpenAPI Specs**: Automatically creates interactive Swagger (`/docs`) and ReDoc (`/redoc`) portals based on Pydantic request models.
* **Middlewares and Lifespan**: Easy setup of class-based middlewares (Request ID tracking, CORS) and startup validation scripts using standard lifespan context hooks.
* **Speed and Performance**: Extremely high performance on par with Go or Node.js.

## Alternatives Considered
* **Flask**: Simple but lacks async capabilities out of the box and requires external dependencies to build OpenAPI/Pydantic schemas.
* **Django**: Heavyweight and overly complex for a service primarily focused on thin API orchestration.
