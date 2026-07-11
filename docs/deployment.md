# Production Deployment Guide

This guide details steps to deploy the Decision Intelligence Platform to cloud environments.

---

## Deployment Architecture

```mermaid
graph TD
    User([End User]) -->|HTTPS| Vercel[Vercel Frontend CDN]
    Vercel -->|API requests / CORS| Railway[Railway Backend Service]

    subgraph Cloud [Production VPC]
        Railway -->|SQL queries| PG[(PostgreSQL Database)]
        Railway -->|Embeddings Search| Qdrant[(Qdrant Cloud Cluster)]
        Railway -.->|Multimodal LLM inference| OpenRouter[OpenRouter API]
    end
```

---

## 1. Backend Service (Railway)

The backend is fully containerized and deploys automatically using Railway's Dockerfile builder.

### Steps
1. Create a new service on Railway.
2. Link your GitHub repository.
3. Railway automatically detects `railway.json` and starts building the container.
4. Expose the API health check on `/api/v1/health`.

---

## 2. Frontend client (Vercel)

The React client compiles static bundles and is served globally via Vercel.

### Steps
1. Create a project in Vercel.
2. Set build directory to `frontend/dist` (or `frontend` root with output directory `dist`).
3. Set the Build Command: `npm run build`
4. Set the Install Command: `npm install`
5. Configure `VITE_API_BASE_URL` to point to your Railway API domain (e.g. `https://my-backend-app.railway.app/api/v1`).

---

## 3. Production Environment Keys

Add these variables to your Railway deployment settings:

| Variable | Description | Recommended Value |
| --- | --- | --- |
| `ENVIRONMENT` | Deployment stage environment. | `production` |
| `LOG_LEVEL` | Logging detail level. | `INFO` |
| `DATABASE_URL` | PostgreSQL connection string. | `postgresql://user:pass@host:port/db` |
| `VECTOR_DB` | Active vector database driver. | `qdrant` |
| `QDRANT_URL` | Remote Qdrant server endpoint. | `https://qdrant-host-instance` |
| `QDRANT_API_KEY` | Remote Qdrant authentication token. | `<secret-token>` |
| `CORS_ORIGINS` | Permitted origins list (JSON array). | `["https://my-app.vercel.app"]` |
| `OPENROUTER_API_KEY` | OpenRouter access token. | `<openrouter-token>` |
