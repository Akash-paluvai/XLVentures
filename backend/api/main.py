import logging
import json
import time
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import uuid

from backend.core.settings import settings
from backend.core.config_loader import load_domain_pack, load_accounts
from backend.registry.agent_registry import bootstrap_agents, get_agent
from backend.core.planner import graph, planner_traces
from backend.memory.episodic import SessionLocal, RecommendationRecord, FeedbackRecord


# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api")

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="FastAPI backend for Agentic Decision Intelligence Platform"
)

# CORS configuration from settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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


# ── Startup ──────────────────────────────────────────────────────────────────

@app.on_event("startup")
def startup_event():
    """On startup, validate domain packs and bootstrap agents."""
    logger.info("Initializing and validating domain packs...")
    for pack_name in ["customer_success", "recruitment"]:
        try:
            load_domain_pack(pack_name)
            logger.info(f"Validated domain pack: '{pack_name}'.")
        except Exception as e:
            logger.error(f"CRITICAL: Failed to validate '{pack_name}': {e}")
            raise RuntimeError(f"Domain pack '{pack_name}' invalid: {e}")

    logger.info("Bootstrapping agents in registry...")
    bootstrap_agents()


# ── Health ───────────────────────────────────────────────────────────────────

@app.get(f"{settings.API_V1_PREFIX}/health")
def get_health():
    return {"status": "healthy"}


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
        domain_pack = load_domain_pack(req.domain_pack_id)
        entities = load_accounts(req.domain_pack_id)

        id_key = "account_id" if req.domain_pack_id == "customer_success" else "candidate_id"
        entity = next((e for e in entities if e.get(id_key) == req.entity_id), None)

        if not entity:
            raise HTTPException(status_code=404, detail=f"Entity '{req.entity_id}' not found.")

        interaction_text = (
            req.interaction
            or entity.get("interaction_notes")
            or entity.get("recruiter_notes")
            or ""
        )

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
            "metadata": {},
        }

        thread_id = str(uuid.uuid4())
        config = {"configurable": {"thread_id": thread_id}}

        logger.info(f"Running graph on thread '{thread_id}' for entity '{req.entity_id}'...")
        t0 = time.time()

        for event in graph.stream(state, config):
            pass

        elapsed_ms = round((time.time() - t0) * 1000)

        checkpoint_state = graph.get_state(config)
        routing_path = checkpoint_state.values.get("metadata", {}).get("routing_path", "unknown")

        # Store trace
        planner_traces[thread_id] = {
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

        return {
            "thread_id": thread_id,
            "recommendation": checkpoint_state.values.get("explanation_output"),
            "routing_path": routing_path,
            "execution_time_ms": elapsed_ms,
            "status": "paused_for_approval",
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


# ── Approve (resumes graph) ─────────────────────────────────────────────────

@app.post(f"{settings.API_V1_PREFIX}/approve")
def post_approve(req: ApproveRequest):
    try:
        config = {"configurable": {"thread_id": req.thread_id}}
        current_state = graph.get_state(config)

        if not current_state.values:
            raise HTTPException(status_code=404, detail=f"Thread '{req.thread_id}' not found.")

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

        logger.info(f"Resuming graph on thread '{req.thread_id}' with outcome '{req.outcome}'...")
        graph.update_state(config, state_updates, as_node="human_approval_node")

        t0 = time.time()
        for event in graph.stream(None, config):
            pass
        elapsed_ms = round((time.time() - t0) * 1000)

        final_state = graph.get_state(config)

        # Update trace
        if req.thread_id in planner_traces:
            trace = planner_traces[req.thread_id]
            trace["paused"] = False
            trace["executed_path"].append("learning_node")
            trace["timestamps"]["completed_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
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
                        "created_at": fb.created_at.isoformat() if fb.created_at else None,
                    }
                    for fb in feedbacks
                ]

                try:
                    rec_data = json.loads(rec.recommendation_json)
                except Exception:
                    rec_data = {}

                results.append({
                    "recommendation_id": rec.recommendation_id,
                    "entity_id": rec.entity_id,
                    "domain_pack_id": rec.domain_pack_id,
                    "recommendation": rec_data,
                    "feedback": fb_list,
                    "created_at": rec.created_at.isoformat() if rec.created_at else None,
                })

        return results

    except Exception as e:
        logger.error(f"History error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Heuristics (learned from reflection) ─────────────────────────────────────

@app.get(f"{settings.API_V1_PREFIX}/heuristics")
def get_heuristics(domain: str = Query("customer_success")):
    """Returns learned heuristics from ChromaDB for a domain."""
    try:
        from backend.memory.semantic import get_document_by_id
        doc = get_document_by_id(domain, "learned_heuristics")
        if not doc:
            return []
        return [{
            "id": doc["id"],
            "content": doc["content"],
            "metadata": doc["metadata"],
        }]

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
            raise HTTPException(status_code=404, detail=f"Trace for thread '{thread_id}' not found.")
        return trace

    # Return all traces (most recent first)
    traces = sorted(planner_traces.values(), key=lambda t: t.get("timestamps", {}).get("started_at", ""), reverse=True)
    return traces


@app.get(f"{settings.API_V1_PREFIX}/traces")
def get_all_traces():
    """Returns all planner execution traces."""
    traces = sorted(planner_traces.values(), key=lambda t: t.get("timestamps", {}).get("started_at", ""), reverse=True)
    return traces
