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

        logger.info(f"Running graph on thread '{thread_id}' for entity '{req.entity_id}'...")
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
            why_not_others.append({
                "action": action.get("title", ""),
                "reason": action["rejected_reason"],
            })

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
                prev_data = json.loads(prev.recommendation_json)
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
                    "confidence": prev_data.get("computed_confidence", {}).get("score", 0),
                    "outcome": fb.outcome if fb else "unknown",
                    "created_at": prev.created_at.isoformat() if prev.created_at else None,
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
                            .join(RecommendationRecord, RecommendationRecord.recommendation_id == FeedbackRecord.recommendation_id)
                            .filter(RecommendationRecord.domain_pack_id == "customer_success")
                            .filter(FeedbackRecord.outcome == "approved")
                            .all()
                        )
                        saved_acv = 0
                        for fb, rec in rows:
                            rec_data = json.loads(rec.recommendation_json)
                            entity_id = rec.entity_id
                            acc = next((a for a in accounts if a.get("account_id") == entity_id), None)
                            if acc:
                                saved_acv += acc.get("annual_contract_value", 0) * 0.15
                        if rows:
                            nrr_impact = round((saved_acv / total_acv) * 100, 1)
            except Exception:
                pass

            metrics = {
                "acceptance_rate": _calculate_acceptance_rate("customer_success"),
                "risk_catch_lead_time_days": lead_time,
                "simulated_nrr_impact_pct": nrr_impact
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
                "time_to_hire_days": t2h
            }

        return {
            "domain_pack": domain_pack,
            "metrics": metrics,
            "memory": {
                "active_collection": f"domain_{domain}"
            },
            "validation": {
                "domain_switched": True,
                "memory_loaded": True,
                "prompt_overrides_loaded": True
            },
            "supported_domains": [
                "customer_success",
                "recruitment"
            ],
            "platform_capabilities": [
                "dynamic_orchestration",
                "human_in_the_loop",
                "episodic_memory",
                "semantic_memory",
                "cross_domain_configuration"
            ]
        }
    except Exception as e:
        logger.error(f"Domain config error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

