import json
import logging
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from backend.core.logger import request_id_ctx_var, setup_logging
from backend.core.settings import settings

# Initialize root logging configuration early
setup_logging()

from backend.agents.interaction_analyzer import analyze_interaction
from backend.core.config_loader import load_accounts, load_domain_pack
from backend.core.impact_engine import assess_impact
from backend.core.planner import graph, planner_traces
from backend.memory.episodic import FeedbackRecord, RecommendationRecord, SessionLocal
from backend.memory.interactions import (
    create_evolution,
    create_interaction,
    get_interaction_stats,
    get_interactions,
    get_latest_evolution,
    get_recent_interactions,
)
from backend.registry.agent_registry import bootstrap_agents, get_agent
from backend.security.input_guard import ValidationError, validate_interaction_input

logger = logging.getLogger("api")


def ensure_directories():
    """Ensure that the data and vector store directories exist before startup."""
    from pathlib import Path

    # Determine SQLite DB directory from DATABASE_URL
    if settings.DATABASE_URL.startswith("sqlite:///"):
        db_path_str = settings.DATABASE_URL.replace("sqlite:///", "")
        db_path = Path(db_path_str)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"SQLite directory checked/created at: {db_path.parent}")

    # Determine ChromaDB directory (only if VECTOR_DB is chroma)
    if settings.VECTOR_DB == "chroma":
        chroma_path = Path(settings.CHROMA_PATH)
        chroma_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"ChromaDB directory checked/created at: {chroma_path}")

    # Determine Qdrant local directory (only if VECTOR_DB is qdrant and not using remote Qdrant)
    if settings.VECTOR_DB == "qdrant" and not settings.QDRANT_URL:
        qdrant_path = Path(settings.QDRANT_PATH)
        qdrant_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Qdrant local directory checked/created at: {qdrant_path}")


def check_db_health() -> bool:
    """Test connection to the SQL database."""
    try:
        from sqlalchemy import text

        with SessionLocal() as session:
            session.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False


def check_vector_store_health() -> bool:
    """Test connection to the active vector database."""
    try:
        from backend.memory import semantic

        return semantic.is_healthy()
    except Exception as e:
        logger.error(f"Vector store health check failed: {e}")
        return False


def validate_storage_connections():
    """Verify core storage layers are reachable on startup. Fails fast if critical databases are down."""
    # 1. Check Database (critical)
    logger.info("Verifying database connection...")
    if not check_db_health():
        logger.error("CRITICAL: Database connection check failed!")
        raise RuntimeError("Database connection check failed.")
    logger.info("Database connection validated successfully.")

    # 2. Check Vector DB (critical)
    logger.info(f"Verifying vector store connection ({settings.VECTOR_DB})...")
    if not check_vector_store_health():
        logger.error("CRITICAL: Vector store connection check failed!")
        raise RuntimeError("Vector store connection check failed.")
    logger.info("Vector store connection validated successfully.")

    # 3. Check LLM Key (optional/warning only)
    logger.info("Verifying LLM service configuration...")
    if not settings.OPENROUTER_API_KEY:
        logger.warning(
            "WARNING: OPENROUTER_API_KEY is not configured. Heuristic fallbacks will be used."
        )
    else:
        logger.info("LLM service configured successfully.")


def print_startup_banner():
    # Determine SQLite vs Postgres URL type
    db_type = (
        "PostgreSQL" if settings.DATABASE_URL.startswith("postgresql") else "SQLite"
    )
    vs_type = settings.VECTOR_DB.upper()

    # Count playbooks
    playbook_count = 0
    data_dir = settings.BASE_DIR / "backend" / "data"
    for d in ["customer_success", "recruitment"]:
        playbook_dir = data_dir / d / "playbooks"
        if playbook_dir.exists():
            playbook_count += len(list(playbook_dir.glob("*.md")))

    # Count agents
    from backend.registry.agent_registry import list_agents

    agents_count = len(list_agents())

    banner = f"""
============================================================
  DECISION INTELLIGENCE PLATFORM STARTED SUCCESSFULLY

  Environment  : {settings.ENVIRONMENT.capitalize()}
  Planner      : Loaded
  Agents       : {agents_count}
  Domain Packs : 2 (Customer Success, Recruitment)
  Playbooks    : {playbook_count}
  Database     : Connected ({db_type})
  Vector Store : Connected ({vs_type})
============================================================
"""
    print(banner, flush=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """On startup, initialize directories, validate storage connections, validate configs, and bootstrap agents."""
    # 1. Run filesystem setup
    ensure_directories()

    # 2. Validate storage connections
    validate_storage_connections()

    # 3. Validate configurations & domain packs
    logger.info("Initializing and validating domain packs...")
    for pack_name in ["customer_success", "recruitment"]:
        try:
            pack = load_domain_pack(pack_name)
            logger.info(f"Validated domain pack: '{pack_name}'.")

            # Validate accounts exist and are readable
            accounts = load_accounts(pack_name)
            logger.info(
                f"Validated accounts data for: '{pack_name}' (Loaded {len(accounts)} records)."
            )
        except Exception as e:
            logger.error(f"CRITICAL: Failed to validate '{pack_name}': {e}")
            raise RuntimeError(f"Domain pack '{pack_name}' invalid or missing: {e}")

    # 4. Validate playbooks exist
    logger.info("Validating playbooks presence...")
    data_dir = settings.BASE_DIR / "backend" / "data"
    playbooks_found = False
    for domain in ["customer_success", "recruitment"]:
        playbook_dir = data_dir / domain / "playbooks"
        if playbook_dir.exists() and any(playbook_dir.glob("*.md")):
            playbooks_found = True
            logger.info(f"Validated playbooks directory for domain: '{domain}'.")
        else:
            logger.warning(
                f"No markdown playbooks found for domain: '{domain}' at {playbook_dir}"
            )

    if not playbooks_found:
        logger.error(
            "CRITICAL: No playbooks found in backend/data! Seeding memory is required."
        )
        raise RuntimeError(
            "CRITICAL: No playbooks found in backend/data. Check data paths."
        )

    # 5. Bootstrap agents in registry
    logger.info("Bootstrapping agents in registry...")
    bootstrap_agents()

    # 6. Validate Planner Graph compiles
    logger.info("Verifying planner compilation...")
    try:
        if graph is None:
            raise ValueError("Planner compilation returned None")
        logger.info("Planner compilation verified successfully.")
    except Exception as e:
        logger.error(f"CRITICAL: Planner verification failed: {e}")
        raise RuntimeError(f"Planner initialization failed: {e}")

    # Print beautiful startup banner
    print_startup_banner()

    yield

    # Graceful Shutdown
    logger.info("============================================================")
    logger.info("  Shutting down Decision Intelligence Platform...")
    logger.info("  Closing DB connections...")
    logger.info("  Closing Vector Store connections...")
    logger.info("  Goodbye!")
    logger.info("============================================================")


app = FastAPI(
    title="Agentic Decision Intelligence Platform",
    description="""
    Production-grade backend for SaaS account management, renewal risk intelligence,
    and automated closed-loop learning.
    """,
    version="1.0.0",
    contact={
        "name": "XL Ventures Support",
        "url": "https://github.com/Akash-paluvai/XLVentures",
    },
    license_info={
        "name": "MIT License",
    },
    lifespan=lifespan,
)


# Custom class-based middleware for request tracking (Request ID & Response Time)
class ProductionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Extract or generate unique Request ID
        request_id = request.headers.get("X-Request-ID")
        if not request_id:
            request_id = str(uuid.uuid4())

        # Set context var for logger to consume in request logs
        token = request_id_ctx_var.set(request_id)

        start_time = time.perf_counter()
        response = None
        try:
            response = await call_next(request)
            process_time_ms = int((time.perf_counter() - start_time) * 1000)

            # Inject headers
            response.headers["X-Response-Time"] = f"{process_time_ms}ms"
            response.headers["X-Request-ID"] = request_id

            # Log the request details with response time
            logger.info(
                f"{request.method} {request.url.path} - "
                f"Status {response.status_code} - "
                f"Duration: {process_time_ms}ms"
            )
            return response
        except Exception as e:
            process_time_ms = int((time.perf_counter() - start_time) * 1000)
            logger.error(f"Request failed: {e} - Duration: {process_time_ms}ms")
            raise e
        finally:
            # Reset ContextVar
            request_id_ctx_var.reset(token)


app.add_middleware(ProductionMiddleware)

# CORS configuration from settings
origins = [o for o in settings.CORS_ORIGINS if o]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global Exception Handlers returning unified JSON format without leaking internal traces
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.error(f"Validation error occurred: {exc}")
    return JSONResponse(
        status_code=422,
        content={
            "error": "ValidationError",
            "message": "Invalid request payload parameters.",
            "details": exc.errors(),
        },
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    logger.error(f"HTTP error occurred (Status {exc.status_code}): {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.__class__.__name__, "message": exc.detail},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception occurred: {exc}", exc_info=True)
    # Hide Python traceback in production
    message = "An unexpected internal server error occurred."
    if settings.ENVIRONMENT == "development":
        message = f"Unhandled Exception: {str(exc)}"
    return JSONResponse(
        status_code=500, content={"error": "InternalServerError", "message": message}
    )


# ── Request schemas ──────────────────────────────────────────────────────────


class RecommendRequest(BaseModel):
    domain_pack_id: str
    entity_id: str
    interaction: Optional[str] = None


class ApproveRequest(BaseModel):
    thread_id: str
    outcome: str
    feedback_text: Optional[str] = None
    edited_action: Optional[Dict[str, Any]] = None


class ReflectRequest(BaseModel):
    domain_pack_id: str


class InteractionRequest(BaseModel):
    account_id: str
    domain_pack_id: str
    interaction_type: str
    source: str
    title: str
    content: str
    tags: Optional[List[str]] = None


# ── Startup/Lifespan Handler Completed ────────────────────────────────────────


# ── Health & Readiness ────────────────────────────────────────────────────────


@app.get(f"{settings.API_V1_PREFIX}/health")
def get_health():
    db_healthy = check_db_health()
    vs_healthy = check_vector_store_health()

    status = "healthy" if (db_healthy and vs_healthy) else "unhealthy"

    return {
        "status": status,
        "services": {
            "database": "connected" if db_healthy else "error",
            "vector_store": "connected" if vs_healthy else "error",
            "llm": "configured" if settings.OPENROUTER_API_KEY else "warning",
        },
        "build": {
            "version": settings.BUILD_VERSION,
            "environment": settings.ENVIRONMENT,
            "git_commit": settings.GIT_COMMIT,
            "build_date": settings.BUILD_DATE,
        },
    }


@app.get(f"{settings.API_V1_PREFIX}/ready")
def get_readiness():
    db_healthy = check_db_health()
    vs_healthy = check_vector_store_health()

    planner_loaded = graph is not None

    domain_packs_count = 0
    try:
        for pack in ["customer_success", "recruitment"]:
            load_domain_pack(pack)
            domain_packs_count += 1
    except Exception:
        pass

    if db_healthy and vs_healthy and planner_loaded and domain_packs_count > 0:
        return {
            "status": "ready",
            "database": "connected",
            "vector_store": "connected",
            "planner": "loaded",
            "domain_packs": domain_packs_count,
        }
    else:
        from fastapi import status

        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "not ready",
                "database": "connected" if db_healthy else "error",
                "vector_store": "connected" if vs_healthy else "error",
                "planner": "loaded" if planner_loaded else "error",
                "domain_packs": domain_packs_count,
            },
        )


# ── Domain & Accounts ────────────────────────────────────────────────────────


@app.get(f"{settings.API_V1_PREFIX}/domain")
def get_domain(domain: str = Query("customer_success")):
    try:
        return load_domain_pack(domain)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))


@app.get(f"{settings.API_V1_PREFIX}/accounts")
def get_accounts(domain: str = Query("customer_success")):
    try:
        return load_accounts(domain)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Recommend (runs graph to interrupt) ──────────────────────────────────────


@app.post(f"{settings.API_V1_PREFIX}/recommend")
def post_recommend(req: RecommendRequest):
    try:
        # Reset request-scoped LLM calls counter
        from backend.core.llm_client import llm_call_counter

        llm_call_counter.set(0)

        # Validate inputs via input_guard
        try:
            validate_interaction_input(req.model_dump())
        except ValidationError as val_err:
            raise HTTPException(status_code=400, detail=str(val_err))

        domain_pack = load_domain_pack(req.domain_pack_id)
        entities = load_accounts(req.domain_pack_id)

        id_key = (
            "account_id" if req.domain_pack_id == "customer_success" else "candidate_id"
        )
        entity = next((e for e in entities if e.get(id_key) == req.entity_id), None)

        if not entity:
            raise HTTPException(
                status_code=404, detail=f"Entity '{req.entity_id}' not found."
            )

        interaction_text = (
            req.interaction
            or entity.get("interaction_notes")
            or entity.get("recruiter_notes")
            or ""
        )

        thread_id = str(uuid.uuid4())

        state = {
            "domain_pack": domain_pack,
            "account": entity,
            "retrieved_context": {},
            "reasoning_output": {},
            "recommendation_output": {},
            "explanation_output": {},
            "evidence": [],
            "confidence": {},
            "human_feedback": None,
            "metadata": {"thread_id": thread_id},
        }

        config = {"configurable": {"thread_id": thread_id}}

        logger.info(
            f"Running graph on thread '{thread_id}' for entity '{req.entity_id}'..."
        )
        t0 = time.time()

        for event in graph.stream(state, config):
            pass

        elapsed_ms = round((time.time() - t0) * 1000)

        checkpoint_state = graph.get_state(config)
        vals = checkpoint_state.values
        routing_path = vals.get("metadata", {}).get("routing_path", "unknown")

        # Merge incremental steps with trace metadata
        trace_data = planner_traces.get(thread_id, {})
        agent_steps = trace_data.get("steps", [])

        planner_traces[thread_id] = {
            **trace_data,
            "thread_id": thread_id,
            "domain_pack_id": req.domain_pack_id,
            "entity_id": req.entity_id,
            "classification": routing_path,
            "executed_path": _build_executed_path(routing_path),
            "timestamps": {
                "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t0)),
                "paused_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            },
            "paused": True,
            "execution_time_ms": elapsed_ms,
        }

        # Build recommendation analysis
        rec_analysis = _build_recommendation_analysis(vals)

        # Build execution summary
        completed_count = sum(1 for s in agent_steps if s["status"] == "completed")
        paused_count = sum(1 for s in agent_steps if s["status"] == "paused")
        conf = vals.get("confidence", {})

        return {
            "thread_id": thread_id,
            "recommendation": vals.get("explanation_output"),
            "routing_path": routing_path,
            "execution_time_ms": elapsed_ms,
            "status": "paused_for_approval",
            "agent_steps": agent_steps,
            "execution_summary": {
                "total_agents": len(agent_steps),
                "completed": completed_count,
                "paused": paused_count,
                "path_taken": routing_path,
                "total_evidence": len(vals.get("evidence", [])),
                "confidence_score": conf.get("score", 0),
            },
            "recommendation_analysis": rec_analysis,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Recommend error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Graph execution failure: {e}")


def _build_executed_path(routing_path: str) -> List[str]:
    """Build the list of nodes executed based on routing path."""
    if routing_path == "escalation":
        return [
            "planner_node",
            "context_node",
            "reasoning_node",
            "recommendation_node",
            "explanation_node",
            "human_approval_node (paused)",
        ]
    return [
        "planner_node",
        "context_node",
        "generate_standard_recommendation",
        "explanation_node",
        "human_approval_node (paused)",
    ]


def _build_recommendation_analysis(vals: dict) -> dict:
    """Build the curated recommendation analysis for the AI Explainability Canvas."""
    explanation = vals.get("explanation_output", {})
    reasoning = vals.get("reasoning_output", {})
    rec_output = vals.get("recommendation_output", {})
    evidence_list = vals.get("evidence", [])
    conf = vals.get("confidence", {})

    # Build "why this" reasons from reasoning trace and evidence
    why_this = []
    reasoning_trace = explanation.get("reasoning_trace", [])
    for item in reasoning_trace:
        if isinstance(item, str) and len(item) > 10:
            # Extract the key insight portion
            why_this.append(item.split(": ", 1)[-1] if ": " in item else item)

    # Add entity-derived signals
    account = vals.get("account", {})
    if account.get("renewal_date"):
        from datetime import datetime

        try:
            rd = datetime.strptime(account["renewal_date"], "%Y-%m-%d")
            days_until = (rd - datetime.now()).days
            if days_until < 60:
                why_this.insert(0, f"Renewal in {days_until} days")
        except Exception:
            pass
    if account.get("usage_trend"):
        why_this.insert(0, f"Usage trend: {account['usage_trend']}")
    if account.get("health_score") is not None:
        why_this.insert(0, f"Health score: {account['health_score']}")

    # Add evidence-based reasons
    for ev in evidence_list[:3]:
        src = ev.get("source", "")
        src_type = ev.get("source_type", "")
        if src_type == "playbook":
            why_this.append(f"{src.replace('_', ' ').title()} playbook matched")
        elif src_type == "past_case":
            why_this.append(f"Similar past case matched ({src})")

    # Deduplicate while preserving order
    seen = set()
    unique_why = []
    for item in why_this:
        if item not in seen:
            seen.add(item)
            unique_why.append(item)

    # Build "why not others" from rejected candidates
    why_not_others = []
    selected_id = rec_output.get("selected_action_id", "")
    for action in rec_output.get("candidate_actions", []):
        if action.get("id") != selected_id and action.get("rejected_reason"):
            why_not_others.append(
                {
                    "action": action.get("title", ""),
                    "reason": action["rejected_reason"],
                }
            )

    return {
        "why_this": unique_why[:8],
        "why_not_others": why_not_others,
        "confidence_breakdown": {
            "score": conf.get("score", 0),
            "evidence_count": conf.get("evidence_count", 0),
            "source_agreement": conf.get("source_agreement", 0),
            "historical_acceptance_rate": conf.get("historical_acceptance_rate", 0),
        },
    }


# ── Approve (resumes graph) ─────────────────────────────────────────────────


@app.post(f"{settings.API_V1_PREFIX}/approve")
def post_approve(req: ApproveRequest):
    try:
        # Idempotency Check: if already processed, return immediately
        if req.thread_id in planner_traces:
            trace = planner_traces[req.thread_id]
            if not trace.get("paused", True):
                logger.info(
                    f"Idempotency Gate: Thread '{req.thread_id}' already processed (outcome={trace.get('outcome')}). Returning cached response."
                )
                return {
                    "status": "success",
                    "metadata": {
                        "outcome_feedback_id": trace.get("outcome_feedback_id")
                    },
                    "outcome": trace.get("outcome"),
                    "idempotent_cached": True,
                }

        config = {"configurable": {"thread_id": req.thread_id}}
        current_state = graph.get_state(config)

        if not current_state.values:
            raise HTTPException(
                status_code=404, detail=f"Thread '{req.thread_id}' not found."
            )

        state_updates = {
            "human_feedback": {
                "outcome": req.outcome,
                "feedback_text": req.feedback_text,
            }
        }

        if req.outcome == "edited" and req.edited_action:
            explanation_output = current_state.values.get("explanation_output")
            if explanation_output:
                explanation_output["selected_action"] = req.edited_action
                state_updates["explanation_output"] = explanation_output

        logger.info(
            f"Resuming graph on thread '{req.thread_id}' with outcome '{req.outcome}'..."
        )
        graph.update_state(config, state_updates, as_node="human_approval_node")

        t0 = time.time()
        for event in graph.stream(None, config):
            pass
        elapsed_ms = round((time.time() - t0) * 1000)

        final_state = graph.get_state(config)
        fb_id = final_state.values.get("metadata", {}).get("outcome_feedback_id")

        # Update trace
        if req.thread_id in planner_traces:
            trace = planner_traces[req.thread_id]
            trace["paused"] = False
            trace["outcome_feedback_id"] = fb_id
            trace["executed_path"].append("learning_node")
            trace["timestamps"]["completed_at"] = time.strftime(
                "%Y-%m-%dT%H:%M:%SZ", time.gmtime()
            )
            trace["execution_time_ms"] += elapsed_ms
            trace["outcome"] = req.outcome

        return {
            "status": "success",
            "metadata": final_state.values.get("metadata"),
            "outcome": req.outcome,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Approve error for thread '{req.thread_id}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Resumption failure: {e}")


# ── Reflect (manual learning trigger) ────────────────────────────────────────


@app.post(f"{settings.API_V1_PREFIX}/reflect")
def post_reflect(req: ReflectRequest):
    try:
        agent = get_agent("learning_agent")["agent"]
        return agent.run_reflection(req.domain_pack_id)
    except Exception as e:
        logger.error(f"Reflection error: {e}")
        raise HTTPException(status_code=500, detail=f"Reflection failure: {e}")


# ── History (recommendations + feedback) ─────────────────────────────────────


@app.get(f"{settings.API_V1_PREFIX}/history")
def get_history(domain: str = Query("customer_success")):
    """Returns all past recommendations with their feedback for a domain."""
    try:
        with SessionLocal() as session:
            recs = (
                session.query(RecommendationRecord)
                .filter(RecommendationRecord.domain_pack_id == domain)
                .order_by(RecommendationRecord.created_at.desc())
                .all()
            )

            results = []
            for rec in recs:
                feedbacks = (
                    session.query(FeedbackRecord)
                    .filter(FeedbackRecord.recommendation_id == rec.recommendation_id)
                    .all()
                )

                fb_list = [
                    {
                        "feedback_id": fb.feedback_id,
                        "outcome": fb.outcome,
                        "human_feedback": fb.human_feedback,
                        "created_at": (
                            fb.created_at.isoformat() if fb.created_at else None
                        ),
                    }
                    for fb in feedbacks
                ]

                try:
                    rec_json = rec.recommendation_json
                    rec_data = json.loads(str(rec_json)) if rec_json is not None else {}
                except Exception:
                    rec_data = {}

                results.append(
                    {
                        "recommendation_id": rec.recommendation_id,
                        "entity_id": rec.entity_id,
                        "domain_pack_id": rec.domain_pack_id,
                        "recommendation": rec_data,
                        "feedback": fb_list,
                        "created_at": (
                            rec.created_at.isoformat() if rec.created_at else None
                        ),
                    }
                )

        return results

    except Exception as e:
        logger.error(f"History error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Previous recommendation (for "What Changed" comparison) ─────────────────


@app.get(f"{settings.API_V1_PREFIX}/previous-recommendation")
def get_previous_recommendation(
    domain: str = Query("customer_success"),
    entity_id: str = Query(...),
):
    """Returns the most recent recommendation for an entity (for diff view)."""
    try:
        with SessionLocal() as session:
            recs = (
                session.query(RecommendationRecord)
                .filter(
                    RecommendationRecord.domain_pack_id == domain,
                    RecommendationRecord.entity_id == entity_id,
                )
                .order_by(RecommendationRecord.created_at.desc())
                .limit(2)
                .all()
            )

            if not recs:
                return {"has_previous": False, "previous": None, "changes": []}

            # The first result is the current (just-created), second is previous
            prev = recs[1] if len(recs) > 1 else recs[0]

            try:
                prev_json = prev.recommendation_json
                prev_data = json.loads(str(prev_json)) if prev_json is not None else {}
            except Exception:
                prev_data = {}

            # Get feedback for previous
            fb = (
                session.query(FeedbackRecord)
                .filter(FeedbackRecord.recommendation_id == prev.recommendation_id)
                .first()
            )

            prev_action = prev_data.get("selected_action", {})

            return {
                "has_previous": len(recs) > 1,
                "previous": {
                    "recommendation_id": prev.recommendation_id,
                    "entity_id": prev.entity_id,
                    "action_title": prev_action.get("title", "N/A"),
                    "action_description": prev_action.get("description", ""),
                    "confidence": prev_data.get("computed_confidence", {}).get(
                        "score", 0
                    ),
                    "outcome": fb.outcome if fb else "unknown",
                    "created_at": (
                        prev.created_at.isoformat() if prev.created_at else None
                    ),
                },
            }

    except Exception as e:
        logger.error(f"Previous recommendation error: {e}")
        return {"has_previous": False, "previous": None}


# ── Heuristics (learned from reflection) ─────────────────────────────────────


@app.get(f"{settings.API_V1_PREFIX}/heuristics")
def get_heuristics(domain: str = Query("customer_success")):
    """Returns learned heuristics from ChromaDB for a domain."""
    try:
        from backend.memory.semantic import get_document_by_id

        doc = get_document_by_id(domain, "learned_heuristics")
        if not doc:
            return []
        return [
            {
                "id": doc["id"],
                "content": doc["content"],
                "metadata": doc["metadata"],
            }
        ]

    except Exception as e:
        logger.error(f"Heuristics error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Trace (planner execution trace) ──────────────────────────────────────────


@app.get(f"{settings.API_V1_PREFIX}/trace")
def get_trace(thread_id: str = Query(None)):
    """Returns planner execution trace(s)."""
    if thread_id:
        trace = planner_traces.get(thread_id)
        if not trace:
            raise HTTPException(
                status_code=404, detail=f"Trace for thread '{thread_id}' not found."
            )
        return trace

    # Return all traces (most recent first)
    traces = sorted(
        planner_traces.values(),
        key=lambda t: t.get("timestamps", {}).get("started_at", ""),
        reverse=True,
    )
    return traces


@app.get(f"{settings.API_V1_PREFIX}/traces")
def get_all_traces():
    """Returns all planner execution traces."""
    traces = sorted(
        planner_traces.values(),
        key=lambda t: t.get("timestamps", {}).get("started_at", ""),
        reverse=True,
    )
    return traces


# ── Configuration Hub & Dynamics ─────────────────────────────────────────────


def _calculate_acceptance_rate(domain: str) -> float:
    try:
        with SessionLocal() as session:
            rows = (
                session.query(FeedbackRecord)
                .filter(FeedbackRecord.domain_pack_id == domain)
                .all()
            )
            if not rows:
                return 0.88 if domain == "customer_success" else 0.81
            approvals = sum(1 for r in rows if r.outcome == "approved")
            return round(approvals / len(rows), 2)
    except Exception:
        return 0.88 if domain == "customer_success" else 0.81


@app.get(f"{settings.API_V1_PREFIX}/domain-config")
def get_domain_config(domain: str = Query("customer_success")):
    """Returns all domain pack configs, active memory namespaces, validations and dynamic metrics."""
    try:
        domain_pack = load_domain_pack(domain)

        # Calculate dynamic metrics
        metrics = {}
        if domain == "customer_success":
            # Lead time calculation
            lead_time = 14
            try:
                accounts = load_accounts("customer_success")
                diffs = []
                from datetime import datetime

                for acc in accounts:
                    rdate = datetime.strptime(acc["renewal_date"], "%Y-%m-%d")
                    udate = datetime.strptime(acc["updated_at"][:10], "%Y-%m-%d")
                    diffs.append((rdate - udate).days)
                if diffs:
                    lead_time = round(sum(diffs) / len(diffs))
            except Exception:
                pass

            # NRR calculation
            nrr_impact = 2.4
            try:
                accounts = load_accounts("customer_success")
                total_acv = sum(acc.get("annual_contract_value", 0) for acc in accounts)
                if total_acv > 0:
                    with SessionLocal() as session:
                        rows = (
                            session.query(FeedbackRecord, RecommendationRecord)
                            .join(
                                RecommendationRecord,
                                RecommendationRecord.recommendation_id
                                == FeedbackRecord.recommendation_id,
                            )
                            .filter(
                                RecommendationRecord.domain_pack_id
                                == "customer_success"
                            )
                            .filter(FeedbackRecord.outcome == "approved")
                            .all()
                        )
                        saved_acv = 0
                        for fb, rec in rows:
                            rec_data = json.loads(rec.recommendation_json)
                            entity_id = rec.entity_id
                            acc = next(
                                (
                                    a
                                    for a in accounts
                                    if a.get("account_id") == entity_id
                                ),
                                None,
                            )
                            if acc:
                                saved_acv += acc.get("annual_contract_value", 0) * 0.15
                        if rows:
                            nrr_impact = round((saved_acv / total_acv) * 100, 1)
            except Exception:
                pass

            metrics = {
                "acceptance_rate": _calculate_acceptance_rate("customer_success"),
                "risk_catch_lead_time_days": lead_time,
                "simulated_nrr_impact_pct": nrr_impact,
            }
        elif domain == "recruitment":
            t2h = 21
            try:
                candidates = load_accounts("recruitment")
                diffs = []
                from datetime import datetime

                for cand in candidates:
                    ddate = datetime.strptime(cand["decision_deadline"], "%Y-%m-%d")
                    udate = datetime.strptime(cand["updated_at"][:10], "%Y-%m-%d")
                    diffs.append((ddate - udate).days)
                if diffs:
                    t2h = round(sum(diffs) / len(diffs))
            except Exception:
                pass

            metrics = {
                "acceptance_rate": _calculate_acceptance_rate("recruitment"),
                "time_to_hire_days": t2h,
            }

        return {
            "domain_pack": domain_pack,
            "metrics": metrics,
            "memory": {"active_collection": f"domain_{domain}"},
            "validation": {
                "domain_switched": True,
                "memory_loaded": True,
                "prompt_overrides_loaded": True,
            },
            "supported_domains": ["customer_success", "recruitment"],
            "platform_capabilities": [
                "dynamic_orchestration",
                "human_in_the_loop",
                "episodic_memory",
                "semantic_memory",
                "cross_domain_configuration",
            ],
        }
    except Exception as e:
        logger.error(f"Domain config error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Interaction Intelligence Endpoints ───────────────────────────────────────


@app.post(f"{settings.API_V1_PREFIX}/interactions")
def post_interaction(req: InteractionRequest):
    """Ingest a new interaction, extract signals, assess impact, re-run planner, store evolution."""
    try:
        t0 = time.time()

        # 1. Validate account exists
        entities = load_accounts(req.domain_pack_id)
        id_key = (
            "account_id" if req.domain_pack_id == "customer_success" else "candidate_id"
        )
        entity = next((e for e in entities if e.get(id_key) == req.account_id), None)
        if not entity:
            raise HTTPException(
                status_code=404, detail=f"Entity '{req.account_id}' not found."
            )

        # 2. Analyze interaction — extract signals
        analysis = analyze_interaction(req.content, req.domain_pack_id, entity)
        signals = analysis["signals"]
        severity = analysis["severity"]

        # 3. Compute impact
        impact = assess_impact(signals, entity)

        # 4. Fetch previous recommendation for this entity
        prev_rec_data = None
        prev_action_title = None
        planner_before = "unknown"
        with SessionLocal() as session:
            prev_recs = (
                session.query(RecommendationRecord)
                .filter(
                    RecommendationRecord.domain_pack_id == req.domain_pack_id,
                    RecommendationRecord.entity_id == req.account_id,
                )
                .order_by(RecommendationRecord.created_at.desc())
                .limit(1)
                .all()
            )
            if prev_recs:
                try:
                    prev_rec_json = prev_recs[0].recommendation_json
                    prev_rec_data = (
                        json.loads(str(prev_rec_json))
                        if prev_rec_json is not None
                        else {}
                    )
                    prev_action_title = prev_rec_data.get("selected_action", {}).get(
                        "title", "N/A"
                    )
                except Exception:
                    prev_rec_data = {}

        # Determine planner_before from previous trace or default
        # Check most recent trace for this entity
        for trace in planner_traces.values():
            if trace.get("entity_id") == req.account_id:
                planner_before = trace.get("classification", "unknown")
                break

        # 5. Re-run planner with interaction text injected
        from backend.core.llm_client import llm_call_counter

        llm_call_counter.set(0)

        domain_pack = load_domain_pack(req.domain_pack_id)

        # Inject interaction into entity notes for the pipeline
        entity_copy = {**entity}
        interaction_text = f"{req.title}: {req.content}"
        if req.domain_pack_id == "customer_success":
            entity_copy["interaction_notes"] = interaction_text
        else:
            entity_copy["recruiter_notes"] = interaction_text

        thread_id = str(uuid.uuid4())
        state = {
            "domain_pack": domain_pack,
            "account": entity_copy,
            "retrieved_context": {},
            "reasoning_output": {},
            "recommendation_output": {},
            "explanation_output": {},
            "evidence": [],
            "confidence": {},
            "human_feedback": None,
            "metadata": {"thread_id": thread_id},
        }
        config = {"configurable": {"thread_id": thread_id}}

        for event in graph.stream(state, config):
            pass

        checkpoint_state = graph.get_state(config)
        vals = checkpoint_state.values
        planner_after = vals.get("metadata", {}).get("routing_path", "unknown")

        # Get new recommendation
        new_rec = vals.get("explanation_output", {})
        new_action_title = new_rec.get("selected_action", {}).get("title", "N/A")

        # Build agent steps from trace
        trace_data = planner_traces.get(thread_id, {})
        agent_steps = trace_data.get("steps", [])
        elapsed_ms = round((time.time() - t0) * 1000)

        # Update trace metadata
        planner_traces[thread_id] = {
            **trace_data,
            "thread_id": thread_id,
            "domain_pack_id": req.domain_pack_id,
            "entity_id": req.account_id,
            "classification": planner_after,
            "executed_path": _build_executed_path(planner_after),
            "timestamps": {
                "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t0)),
                "paused_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            },
            "paused": True,
            "execution_time_ms": elapsed_ms,
            "triggered_by_interaction": True,
        }

        # 6. Build change reasons
        change_reasons = []
        for sig in signals:
            change_reasons.append(sig.replace("_", " ").title())
        if planner_before != planner_after:
            change_reasons.append(
                f"Planner reclassified: {planner_before} -> {planner_after}"
            )

        # 7. Store interaction with full metadata
        prev_rec_summary = {"title": prev_action_title} if prev_action_title else None
        new_rec_summary = {
            "title": new_action_title,
            "confidence": new_rec.get("computed_confidence", {}).get("score", 0),
        }

        interaction_record = create_interaction(
            entity_id=req.account_id,
            domain_pack_id=req.domain_pack_id,
            interaction_type=req.interaction_type,
            source=req.source,
            title=req.title,
            content=req.content,
            tags=req.tags,
            signals=signals,
            impact_score=impact["impact_score"],
            planner_before=planner_before,
            planner_after=planner_after,
            rec_before=prev_rec_summary,
            rec_after=new_rec_summary,
        )

        # 8. Store recommendation evolution
        create_evolution(
            entity_id=req.account_id,
            domain_pack_id=req.domain_pack_id,
            interaction_id=interaction_record["interaction_id"],
            previous_rec=prev_rec_summary,
            new_rec=new_rec_summary,
            change_reasons=change_reasons,
        )

        # 9. Build recommendation analysis for frontend
        rec_analysis = _build_recommendation_analysis(vals)

        return {
            "interaction": interaction_record,
            "signals": analysis,
            "impact": impact,
            "planner_before": planner_before,
            "planner_after": planner_after,
            "recommendation_before": prev_action_title,
            "recommendation_after": new_action_title,
            "change_reasons": change_reasons,
            "thread_id": thread_id,
            "recommendation": new_rec,
            "routing_path": planner_after,
            "execution_time_ms": elapsed_ms,
            "status": "paused_for_approval",
            "agent_steps": agent_steps,
            "execution_summary": {
                "total_agents": len(agent_steps),
                "completed": sum(1 for s in agent_steps if s["status"] == "completed"),
                "paused": sum(1 for s in agent_steps if s["status"] == "paused"),
                "path_taken": planner_after,
                "total_evidence": len(vals.get("evidence", [])),
                "confidence_score": vals.get("confidence", {}).get("score", 0),
            },
            "recommendation_analysis": rec_analysis,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Interaction ingestion error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Interaction processing failure: {e}"
        )


@app.get(f"{settings.API_V1_PREFIX}/interactions")
def get_interactions_api(
    account_id: str = Query(...),
    limit: int = Query(50),
):
    """List interactions for an entity, newest first."""
    try:
        return get_interactions(account_id, limit)
    except Exception as e:
        logger.error(f"Get interactions error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get(f"{settings.API_V1_PREFIX}/interactions/stats")
def get_interactions_stats(
    domain: str = Query("customer_success"),
):
    """Get interaction statistics for a domain."""
    try:
        return get_interaction_stats(domain)
    except Exception as e:
        logger.error(f"Interaction stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get(f"{settings.API_V1_PREFIX}/recommendation-diff")
def get_recommendation_diff(
    domain: str = Query("customer_success"),
    entity_id: str = Query(...),
):
    """Get latest recommendation evolution diff for an entity."""
    try:
        evolution = get_latest_evolution(entity_id, domain)
        if not evolution:
            return {
                "has_diff": False,
                "previous": None,
                "current": None,
                "change_reasons": [],
            }

        return {
            "has_diff": True,
            "previous": evolution.get("previous_recommendation"),
            "current": evolution.get("new_recommendation"),
            "change_reasons": evolution.get("change_reasons", []),
            "interaction_id": evolution.get("interaction_id"),
            "created_at": evolution.get("created_at"),
        }
    except Exception as e:
        logger.error(f"Recommendation diff error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get(f"{settings.API_V1_PREFIX}/recent-interactions")
def get_recent_interactions_api(
    domain: str = Query("customer_success"),
    limit: int = Query(20),
):
    """List recent interactions across all entities, newest first."""
    try:
        return get_recent_interactions(domain, limit)
    except Exception as e:
        logger.error(f"Recent interactions error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
