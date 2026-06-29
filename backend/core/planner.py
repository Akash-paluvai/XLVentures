"""
Planner Agent — dynamic orchestrator for the Agentic Decision Intelligence Platform.

Constructs the LangGraph StateGraph mapping state flow from Context Agent to
Learning Agent, using checkpointer-based human interrupts and dynamic routing paths.
"""

import os
import json
import logging
import time
import requests
from typing import Dict, Any, List

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from backend.core.state import PlatformState
from backend.registry.agent_registry import get_agent

logger = logging.getLogger(__name__)

# In-memory trace storage (acceptable for hackathon scope)
planner_traces: Dict[str, Any] = {}


# ---------------------------------------------------------------------------
# Step recording helper
# ---------------------------------------------------------------------------

def _record_step(state: PlatformState, agent_name: str, started_at: float,
                 duration_ms: float, input_summary: str, output_summary: str,
                 status: str = "completed", metadata: dict = None):
    """Append an agent execution step to the trace for this thread."""
    thread_id = (state.get("metadata") or {}).get("thread_id")
    if not thread_id:
        return
    planner_traces.setdefault(thread_id, {"steps": []})
    planner_traces[thread_id]["steps"].append({
        "agent": agent_name,
        "status": status,
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(started_at)),
        "duration_ms": round(duration_ms),
        "input_summary": input_summary,
        "output_summary": output_summary,
        "metadata": metadata or {},
    })


# ---------------------------------------------------------------------------
# OpenRouter configuration for classification (optional)
# ---------------------------------------------------------------------------
_OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
_OPENROUTER_MODEL = "google/gemma-3-27b-it:free"
_OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


def _clean_json_response(content: str) -> dict:
    cleaned = content.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    return json.loads(cleaned.strip())


def _entity_summary(state: PlatformState) -> str:
    """Build a short entity summary string for input_summary fields."""
    acc = state.get("account", {})
    entity_id = acc.get("account_id") or acc.get("candidate_id") or "unknown"
    name = acc.get("company_name") or acc.get("candidate_name") or entity_id
    health = acc.get("health_score")
    fit = acc.get("fit_score")
    trend = acc.get("usage_trend", "")
    parts = [f"{name} ({entity_id})"]
    if health is not None:
        parts.append(f"health={health}")
    if fit is not None:
        parts.append(f"fit={fit}")
    if trend:
        parts.append(f"trend={trend}")
    return ", ".join(parts)


# ---------------------------------------------------------------------------
# LangGraph Nodes
# ---------------------------------------------------------------------------

def planner_node(state: PlatformState) -> dict:
    """Classifies the situation as needing 'escalation' or 'standard' processing."""
    t0 = time.time()

    interaction = state.get("account", {}).get("interaction_notes", "") or state.get("account", {}).get("recruiter_notes", "") or ""
    health = state.get("account", {}).get("health_score")

    fit_score = state.get("account", {}).get("fit_score")
    
    interaction_lower = interaction.lower()
    is_urgent = False
    
    # CS critical signals
    if health is not None and health < 50:
        is_urgent = True
    if any(k in interaction_lower for k in ["outage", "latency", "breach", "angry", "terminate", "churn", "decline", "left", "departed"]):
        is_urgent = True
        
    # Recruitment critical signals
    if fit_score is not None and fit_score < 60:
        is_urgent = True
    if any(k in interaction_lower for k in ["dropout", "no response", "quiet", "disengaged", "counter"]):
        is_urgent = True
        
    path = "escalation" if is_urgent else "standard"
    
    # Try LLM classification if API key is set
    if _OPENROUTER_API_KEY:
        try:
            prompt = (
                f"You are the Planner Agent in a Decision Intelligence Platform.\n"
                f"Classify this interaction note and entity context as 'escalation' or 'standard'.\n"
                f"Choose 'escalation' if there are risks of churn, outages, SLA issues, champion departure, candidate disengagement, or salary negotiation.\n"
                f"Otherwise choose 'standard'.\n\n"
                f"Interaction: \"{interaction}\"\n"
                f"Entity Details: {json.dumps(state.get('account'))}\n\n"
                f"Format output as JSON: {{\"path\": \"escalation\" or \"standard\"}}\n"
                f"Output raw JSON only."
            )
            resp = requests.post(
                _OPENROUTER_URL,
                headers={
                    "Authorization": f"Bearer {_OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": _OPENROUTER_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 50,
                    "temperature": 0.1,
                },
                timeout=10,
            )
            resp.raise_for_status()
            res_json = _clean_json_response(resp.json()["choices"][0]["message"]["content"])
            val = res_json.get("path", "standard")
            if val in ["escalation", "standard"]:
                path = val
        except Exception as e:
            logger.warning(f"Planner LLM classification failed: {e}. Using heuristics.")

    meta = state.get("metadata") or {}
    meta = {
        **meta,
        "routing_path": path,
    }

    duration_ms = (time.time() - t0) * 1000
    
    # Build reason string
    reasons = []
    if health is not None and health < 50:
        reasons.append(f"Health score {health} below threshold")
    if is_urgent and not reasons:
        reasons.append("Critical signals detected in interaction")
    if not reasons:
        reasons.append("No urgent signals detected")

    _record_step(
        state, "planner", t0, duration_ms,
        input_summary=_entity_summary(state),
        output_summary=f"Classification: {path}. {'. '.join(reasons)}.",
        metadata={"routing_path": path, "reason": reasons}
    )
    
    logger.info(f"PlannerAgent: Classified interaction path as '{path}'.")
    return {"metadata": meta}


def context_node(state: PlatformState) -> dict:
    """Retrieve semantic and episodic context using ContextAgent."""
    t0 = time.time()

    agent = get_agent("context_agent")["agent"]
    out = agent.run({
        "domain_pack_id": state["domain_pack"]["id"],
        "entity": state["account"],
        "interaction": state["account"].get("interaction_notes") or state["account"].get("recruiter_notes") or "",
    })

    duration_ms = (time.time() - t0) * 1000

    # Build retrieved items list for display
    retrieved_items = []
    for pb in out.get("playbooks", []):
        retrieved_items.append(f"✓ {pb.get('id', 'Playbook').replace('_', ' ').title()}")
    for i, case in enumerate(out.get("past_cases", [])):
        retrieved_items.append(f"✓ Similar Case #{case.get('recommendation_id', i + 1)}")

    ctx_meta = out.get("metadata", {})
    _record_step(
        state, "context", t0, duration_ms,
        input_summary=f"Query: {ctx_meta.get('query', 'N/A')}",
        output_summary=f"Retrieved {ctx_meta.get('playbook_count', 0)} playbook(s), {ctx_meta.get('past_case_count', 0)} similar case(s). Top: {ctx_meta.get('top_evidence', 'none')}.",
        metadata={
            "query": ctx_meta.get("query", ""),
            "playbook_count": ctx_meta.get("playbook_count", 0),
            "past_case_count": ctx_meta.get("past_case_count", 0),
            "top_evidence": ctx_meta.get("top_evidence", "none"),
            "latency_ms": ctx_meta.get("latency_ms", 0),
            "retrieved_items": retrieved_items,
            "missing_information": out.get("missing_information", []),
        }
    )

    return {
        "retrieved_context": out,
        "evidence": out.get("evidence", []),
    }


def reasoning_node(state: PlatformState) -> dict:
    """Run full reasoning analysis."""
    t0 = time.time()

    agent = get_agent("reasoning_agent")["agent"]
    out = agent.run({
        "domain_pack_id": state["domain_pack"]["id"],
        "entity": state["account"],
        "interaction": state["account"].get("interaction_notes") or state["account"].get("recruiter_notes") or "",
        "retrieved_context": state["retrieved_context"],
    })

    duration_ms = (time.time() - t0) * 1000

    risks = out.get("risks", [])
    opps = out.get("opportunities", [])
    missing = out.get("missing_information", [])

    _record_step(
        state, "reasoning", t0, duration_ms,
        input_summary=f"Context with {len(state.get('evidence', []))} evidence nodes",
        output_summary=f"{len(risks)} risk(s), {len(opps)} opportunity(ies), {len(missing)} missing field(s).",
        metadata={
            "risks": risks[:5],
            "opportunities": opps[:3],
            "missing_information": missing,
            "reasoning_summary": out.get("reasoning_summary", ""),
        }
    )

    return {"reasoning_output": out}



def recommendation_node(state: PlatformState) -> dict:
    """Generate ranked recommendations."""
    t0 = time.time()

    agent = get_agent("recommendation_agent")["agent"]
    out = agent.run({
        "domain_pack_id": state["domain_pack"]["id"],
        "entity": state["account"],
        "interaction": state["account"].get("interaction_notes") or state["account"].get("recruiter_notes") or "",
        "retrieved_context": state["retrieved_context"],
        "reasoning_output": state["reasoning_output"],
    })

    duration_ms = (time.time() - t0) * 1000

    actions = out.get("candidate_actions", [])
    selected_id = out.get("selected_action_id", "")
    selected = next((a for a in actions if a.get("id") == selected_id), None)

    _record_step(
        state, "recommendation", t0, duration_ms,
        input_summary=f"Reasoning with {len(state.get('reasoning_output', {}).get('risks', []))} risks",
        output_summary=f"Generated {len(actions)} candidate action(s). Selected: {selected.get('title', 'N/A') if selected else 'N/A'}.",
        metadata={
            "candidate_count": len(actions),
            "selected_action": selected.get("title", "") if selected else "",
            "candidates": [
                {
                    "title": a.get("title", ""),
                    "confidence": a.get("confidence", 0),
                    "rejected_reason": a.get("rejected_reason"),
                }
                for a in actions
            ],
        }
    )

    return {"recommendation_output": out}


def generate_standard_recommendation_node(state: PlatformState) -> dict:
    """Generate default routine/standard recommendation for non-escalation paths."""
    t0 = time.time()

    domain_id = state["domain_pack"]["id"]
    
    # Stub reasoning output
    reasoning_output = {
        "reasoning_summary": "Account is operating within normal boundaries. No critical risks identified.",
        "risks": [],
        "opportunities": ["Regular touchpoint to build relationship stability."],
        "missing_information": state["retrieved_context"].get("missing_information", []),
        "conflicts": [],
    }

    if domain_id == "customer_success":
        recommendation_output = {
            "candidate_actions": [
                {
                    "id": "conduct_quarterly_health_check",
                    "title": "Conduct Quarterly Health Check",
                    "description": "Schedule a routine check-in call to review platform usage and ensure the team is satisfied.",
                    "rationale": "Proactive regular touchpoints prevent drift and maintain high customer satisfaction.",
                    "expected_impact": "Confirm account stability and maintain high health score.",
                    "confidence": 0.85,
                    "business_value_score": 75.0,
                    "feasibility_score": 95.0,
                    "rejected_reason": None,
                },
                {
                    "id": "share_best_practices",
                    "title": "Share Industry Best Practices Guide",
                    "description": "Send a curated guide on how similar companies optimize their platform workflows.",
                    "rationale": "Provide continuous self-service value to help them get more out of the product.",
                    "expected_impact": "Increase feature discovery and usage efficiency.",
                    "confidence": 0.80,
                    "business_value_score": 65.0,
                    "feasibility_score": 98.0,
                    "rejected_reason": "Sending resource guides is a good follow-up but less impactful than a direct relationship touchpoint.",
                },
                {
                    "id": "request_case_study",
                    "title": "Request Co-Marketing Case Study",
                    "description": "Reach out to see if they would be willing to participate in a co-marketing case study highlighting their success.",
                    "rationale": "Leverage a healthy, stable account to generate marketing collateral.",
                    "expected_impact": "Build referenceable customer materials.",
                    "confidence": 0.75,
                    "business_value_score": 60.0,
                    "feasibility_score": 70.0,
                    "rejected_reason": "A case study request should follow a successful health check-in rather than initiating it.",
                },
            ],
            "selected_action_id": "conduct_quarterly_health_check",
        }
    else:  # recruitment
        recommendation_output = {
            "candidate_actions": [
                {
                    "id": "standard_screening",
                    "title": "Schedule Standard Screening Call",
                    "description": "Arrange a 30-minute introductory phone screening.",
                    "rationale": "Candidate is in early screening phase; intro call determines fit.",
                    "expected_impact": "Confirm basic candidate alignment.",
                    "confidence": 0.80,
                    "business_value_score": 80.0,
                    "feasibility_score": 90.0,
                    "rejected_reason": None,
                },
                {
                    "id": "request_coding_sample",
                    "title": "Request Technical Coding Sample",
                    "description": "Send a coding challenge to assess candidate's technical depth.",
                    "rationale": "Standard vetting practice prior to technical interview loops.",
                    "expected_impact": "Establish coding capability.",
                    "confidence": 0.75,
                    "business_value_score": 70.0,
                    "feasibility_score": 85.0,
                    "rejected_reason": "Introductory phone screen is required before requesting technical exercises.",
                },
                {
                    "id": "send_company_overview",
                    "title": "Send Company Overview Package",
                    "description": "Email details regarding culture, benefits, and team structures.",
                    "rationale": "Proactively share resources to secure candidate interest.",
                    "expected_impact": "Excite candidate about the company.",
                    "confidence": 0.70,
                    "business_value_score": 60.0,
                    "feasibility_score": 95.0,
                    "rejected_reason": "Best shared during or after the introductory call rather than beforehand.",
                },
            ],
            "selected_action_id": "standard_screening",
        }

    duration_ms = (time.time() - t0) * 1000
    
    actions = recommendation_output["candidate_actions"]
    selected_id = recommendation_output["selected_action_id"]
    selected = next((a for a in actions if a.get("id") == selected_id), None)

    # Record both reasoning and recommendation steps for standard path
    _record_step(
        state, "reasoning", t0, duration_ms * 0.4,
        input_summary=f"Context with {len(state.get('evidence', []))} evidence nodes",
        output_summary="No critical risks. Standard cadence recommended.",
        metadata={
            "risks": [],
            "opportunities": reasoning_output["opportunities"],
            "missing_information": reasoning_output.get("missing_information", []),
            "reasoning_summary": reasoning_output["reasoning_summary"],
        }
    )

    _record_step(
        state, "recommendation", t0 + (duration_ms * 0.4 / 1000), duration_ms * 0.6,
        input_summary="Standard path — no escalation risks",
        output_summary=f"Generated {len(actions)} candidate action(s). Selected: {selected.get('title', 'N/A') if selected else 'N/A'}.",
        metadata={
            "candidate_count": len(actions),
            "selected_action": selected.get("title", "") if selected else "",
            "candidates": [
                {
                    "title": a.get("title", ""),
                    "confidence": a.get("confidence", 0),
                    "rejected_reason": a.get("rejected_reason"),
                }
                for a in actions
            ],
        }
    )

    return {
        "reasoning_output": reasoning_output,
        "recommendation_output": recommendation_output,
    }


def explanation_node(state: PlatformState) -> dict:
    """Run explanation agent and compute logical confidence score."""
    t0 = time.time()

    agent = get_agent("explanation_agent")["agent"]
    out = agent.run({
        "domain_pack_id": state["domain_pack"]["id"],
        "entity": state["account"],
        "interaction": state["account"].get("interaction_notes") or state["account"].get("recruiter_notes") or "",
        "retrieved_context": state["retrieved_context"],
        "reasoning_output": state["reasoning_output"],
        "recommendation_output": state["recommendation_output"],
    })

    duration_ms = (time.time() - t0) * 1000

    conf = out.get("computed_confidence", {})
    _record_step(
        state, "explanation", t0, duration_ms,
        input_summary=f"Recommendation + {len(state.get('evidence', []))} evidence nodes",
        output_summary=f"Confidence: {round(conf.get('score', 0) * 100)}%. Evidence: {conf.get('evidence_count', 0)} nodes. Trace compiled.",
        metadata={
            "confidence_score": conf.get("score", 0),
            "evidence_count": conf.get("evidence_count", 0),
            "source_agreement": conf.get("source_agreement", 0),
            "historical_acceptance_rate": conf.get("historical_acceptance_rate", 0),
        }
    )
    
    return {
        "explanation_output": out,
        "evidence": out.get("evidence", []),
        "confidence": out.get("computed_confidence", {}),
    }


def human_approval_node(state: PlatformState) -> dict:
    """Human-in-the-loop checkpoint. The graph pauses before entering this node."""
    t0 = time.time()
    logger.info("PlannerAgent: human approval node entered/resumed.")

    _record_step(
        state, "human_approval", t0, 0,
        input_summary="Recommendation ready for human review",
        output_summary="Awaiting approval/edit/reject",
        status="paused",
    )

    return {}


def learning_node(state: PlatformState) -> dict:
    """Commit human outcome decision and run reflective learning."""
    t0 = time.time()

    agent = get_agent("learning_agent")["agent"]
    
    # Extract outcome and feedback from state or set default
    feedback_dict = state.get("human_feedback") or {}
    outcome = feedback_dict.get("outcome", "approved")
    human_feedback = feedback_dict.get("feedback_text", "Approved automatically.")
    
    # Explanation output acts as the final recommendation payload
    rec = state["explanation_output"]
    domain_id = state["domain_pack"]["id"]
    entity_id = state["account"]["account_id"] if domain_id == "customer_success" else state["account"]["candidate_id"]

    # Write outcome to SQLite episodic memory
    fb_id = agent.write_outcome(
        domain_pack_id=domain_id,
        entity_id=entity_id,
        recommendation=rec,
        human_feedback=human_feedback,
        outcome=outcome,
    )

    # Decoupled reflection writeback
    reflection = agent.run_reflection(domain_id)

    duration_ms = (time.time() - t0) * 1000

    _record_step(
        state, "learning", t0, duration_ms,
        input_summary=f"Outcome: {outcome}. Feedback: {human_feedback[:80]}",
        output_summary=f"Episodic memory updated. Reflection: {reflection.get('status', 'unknown')}.",
        metadata={
            "outcome": outcome,
            "feedback_id": fb_id,
            "reflection_status": reflection.get("status"),
            "recommendation_saved": True,
            "feedback_saved": True,
        }
    )

    meta = state.get("metadata") or {}
    meta = {
        **meta,
        "outcome_feedback_id": fb_id,
        "reflection_status": reflection.get("status"),
    }
    return {"metadata": meta}


# ---------------------------------------------------------------------------
# Routing edges
# ---------------------------------------------------------------------------

def route_after_context(state: PlatformState) -> str:
    """Route standard vs escalation flows after context ingestion."""
    path = state.get("metadata", {}).get("routing_path", "standard")
    if path == "escalation":
        return "escalation_route"
    return "standard_route"


# ---------------------------------------------------------------------------
# Graph Compilation
# ---------------------------------------------------------------------------

workflow = StateGraph(PlatformState)

# Add Nodes
workflow.add_node("planner_node", planner_node)
workflow.add_node("context_node", context_node)
workflow.add_node("reasoning_node", reasoning_node)
workflow.add_node("recommendation_node", recommendation_node)
workflow.add_node("generate_standard_recommendation", generate_standard_recommendation_node)
workflow.add_node("explanation_node", explanation_node)
workflow.add_node("human_approval_node", human_approval_node)
workflow.add_node("learning_node", learning_node)

# Set Entry
workflow.set_entry_point("planner_node")

# Define static edges
workflow.add_edge("planner_node", "context_node")

# Add Conditional Split
workflow.add_conditional_edges(
    "context_node",
    route_after_context,
    {
        "escalation_route": "reasoning_node",
        "standard_route": "generate_standard_recommendation",
    }
)

# Connect escalation path
workflow.add_edge("reasoning_node", "recommendation_node")
workflow.add_edge("recommendation_node", "explanation_node")

# Connect standard path
workflow.add_edge("generate_standard_recommendation", "explanation_node")

# Connect end flows
workflow.add_edge("explanation_node", "human_approval_node")
workflow.add_edge("human_approval_node", "learning_node")
workflow.add_edge("learning_node", END)

# Checkpointer memory persistence
checkpointer = MemorySaver()

# Compile the graph, setting human_approval_node as the interrupt barrier
graph = workflow.compile(
    checkpointer=checkpointer,
    interrupt_before=["human_approval_node"],
)
