# Production Deployment Guide

This guide details steps to configure, containerize, and deploy the **Decision Intelligence Platform** to cloud environments using **Railway** (backend API), **Vercel** (frontend client), **PostgreSQL** (relational episodic database), and **Qdrant Cloud** (vector semantic memory).

---

## 1. Production Cloud Topology

```mermaid
graph TD
    User([End User Browser]) -->|HTTPS| Vercel[Vercel Global CDN: Frontend SPA]
    Vercel -->|API Calls / CORS| Railway[Railway VPC: FastAPI Backend Container]

    subgraph Managed Cloud Infrastructure [Production VPC & Services]
        Railway -->|SQL Transactions| Postgres[(Managed PostgreSQL Database)]
        Railway -->|Vector Queries| Qdrant[(Qdrant Cloud Cluster)]
        Railway -.->|LLM Inference| OpenRouter[OpenRouter API]
    end
```

---

## 2. Containerization & Local Stack

The repository includes a production-tuned `Dockerfile` and `docker-compose.yml` for running local or containerized instances.

### 2.1 Building and Running via Docker Compose
```bash
# Build and launch all services in detached mode
docker-compose up --build -d

# Verify container health
docker-compose ps

# View backend logs
docker-compose logs -f backend
```

### 2.2 Dockerfile Specifications
- **Base Image**: `python:3.11-slim`
- **Security**: Runs under non-root user (`appuser`, UID 10001).
- **Optimization**: Caching layer for `requirements.txt` installs.
- **Port Exposure**: Exposes port `8000`.

---

## 3. Backend Cloud Deployment (Railway)

The backend service is containerized and deploys automatically on Railway using `railway.json`.

### 3.1 Setup Instructions:
1. Log into [Railway.app](https://railway.app/) and create a **New Project**.
2. Select **Deploy from GitHub repo** and choose `Akash-paluvai/XLVentures`.
3. Railway automatically detects `railway.json` and builds the Docker container.
4. Configure the **Healthcheck Path** to `/api/v1/health`.
5. Configure the **Readiness Path** to `/api/v1/ready`.

### 3.2 Railway Configuration (`railway.json`):
```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "DOCKERFILE",
    "dockerfilePath": "Dockerfile"
  },
  "deploy": {
    "healthcheckPath": "/api/v1/health",
    "healthcheckTimeout": 100,
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 5
  }
}
```

---

## 4. Frontend Cloud Deployment (Vercel)

The React single-page application compiles static bundles and is served globally via Vercel's Edge CDN.

### 4.1 Setup Instructions:
1. Log into [Vercel.com](https://vercel.com/) and click **Add New Project**.
2. Import `Akash-paluvai/XLVentures`.
3. Configure project settings:
   - **Root Directory**: `frontend`
   - **Framework Preset**: `Vite`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
   - **Install Command**: `npm install`
4. Add Environment Variable:
   - `VITE_API_BASE_URL`: `https://<your-railway-domain>.up.railway.app/api/v1`
5. Click **Deploy**.

---

## 5. Managed Storage Setup

### 5.1 Relational Database (PostgreSQL)
1. Provision a PostgreSQL instance (e.g. Supabase, Railway Postgres, or AWS RDS).
2. Obtain the connection string (`postgresql://user:password@host:5432/dbname`).
3. Set `DATABASE_URL` in your Railway environment variables. The SQLAlchemy engine in `episodic.py` will automatically create all tables on startup.

### 5.2 Vector Database (Qdrant Cloud)
1. Create a free cluster on [Qdrant Cloud](https://cloud.qdrant.io/).
2. Obtain your cluster URL (`https://<cluster-id>.<region>.qdrant.tech:6333`) and API Key.
3. In Railway environment variables, set:
   - `VECTOR_DB=qdrant`
   - `QDRANT_URL=https://<cluster-id>.<region>.qdrant.tech:6333`
   - `QDRANT_API_KEY=<your-qdrant-api-key>`

---

## 6. Complete Environment Variables Matrix

Configure these keys in Railway's **Variables** tab:

| Variable | Type | Description | Recommended Value |
| --- | --- | --- | --- |
| `ENVIRONMENT` | String | Environment tier name | `production` |
| `LOG_LEVEL` | String | Log verbosity level | `INFO` |
| `DATABASE_URL` | String | Connection URL for episodic storage | `postgresql://user:pass@host:5432/db` |
| `VECTOR_DB` | String | Active vector store driver (`chroma` / `qdrant`) | `qdrant` |
| `QDRANT_URL` | String | Remote Qdrant cluster endpoint | `https://<cluster-id>.qdrant.tech:6333` |
| `QDRANT_API_KEY` | String | Remote Qdrant API access key | `<secret-key>` |
| `CORS_ORIGINS` | JSON List | Permitted frontend origins | `["https://xlventures.vercel.app"]` |
| `OPENROUTER_API_KEY` | String | OpenRouter API key for LLM calls | `sk-or-v1-...` |
| `LANGSMITH_TRACING` | String | Enable LangChain tracing | `true` |
| `LANGSMITH_API_KEY` | String | LangSmith API key | `lsv2_pt_...` |
| `LANGSMITH_PROJECT` | String | LangSmith project name | `agentic-decision-platform` |

---

## 7. Verification & Monitoring Probes

After deployment, verify that your service is healthy using the health and readiness endpoints:

### Health Check Endpoint
```bash
curl -s https://<your-railway-domain>.up.railway.app/api/v1/health
```
**Sample Response**:
```json
{
  "status": "healthy",
  "services": {
    "database": "connected",
    "vector_store": "connected",
    "llm": "configured"
  },
  "build": {
    "version": "1.0.0",
    "environment": "production",
    "git_commit": "a77f757",
    "build_date": "2026-07-20"
  }
}
```

### Readiness Check Endpoint
```bash
curl -s https://<your-railway-domain>.up.railway.app/api/v1/ready
```
**Sample Response**:
```json
{
  "status": "ready",
  "database": "connected",
  "vector_store": "connected",
  "planner": "loaded",
  "domain_packs": 2
}
```
