"""
Planner Agent — dynamic orchestrator for the Agentic Decision Intelligence Platform.

Constructs the LangGraph StateGraph mapping state flow from Context Agent to
Learning Agent, using checkpointer-based human interrupts and dynamic routing paths.
"""

import os
import json
import logging
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


# ---------------------------------------------------------------------------
# LangGraph Nodes
# ---------------------------------------------------------------------------

def planner_node(state: PlatformState) -> dict:
    """Classifies the situation as needing 'escalation' or 'standard' processing."""
    interaction = state.get("account", {}).get("interaction_notes", "") or ""
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
    
    logger.info(f"PlannerAgent: Classified interaction path as '{path}'.")
    return {"metadata": meta}


def context_node(state: PlatformState) -> dict:
    """Retrieve semantic and episodic context using ContextAgent."""
    agent = get_agent("context_agent")["agent"]
    out = agent.run({
        "domain_pack_id": state["domain_pack"]["id"],
        "entity": state["account"],
        "interaction": state["account"]["interaction_notes"],
    })
    return {
        "retrieved_context": out,
        "evidence": out.get("evidence", []),
    }


def reasoning_node(state: PlatformState) -> dict:
    """Run full reasoning analysis."""
    agent = get_agent("reasoning_agent")["agent"]
    out = agent.run({
        "domain_pack_id": state["domain_pack"]["id"],
        "entity": state["account"],
        "interaction": state["account"]["interaction_notes"],
        "retrieved_context": state["retrieved_context"],
    })
    return {"reasoning_output": out}


def recommendation_node(state: PlatformState) -> dict:
    """Generate ranked recommendations."""
    agent = get_agent("recommendation_agent")["agent"]
    out = agent.run({
        "domain_pack_id": state["domain_pack"]["id"],
        "entity": state["account"],
        "interaction": state["account"]["interaction_notes"],
        "retrieved_context": state["retrieved_context"],
        "reasoning_output": state["reasoning_output"],
    })
    return {"recommendation_output": out}


def generate_standard_recommendation_node(state: PlatformState) -> dict:
    """Generate default routine/standard recommendation for non-escalation paths."""
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

    return {
        "reasoning_output": reasoning_output,
        "recommendation_output": recommendation_output,
    }


def explanation_node(state: PlatformState) -> dict:
    """Run explanation agent and compute logical confidence score."""
    agent = get_agent("explanation_agent")["agent"]
    out = agent.run({
        "domain_pack_id": state["domain_pack"]["id"],
        "entity": state["account"],
        "interaction": state["account"]["interaction_notes"],
        "retrieved_context": state["retrieved_context"],
        "reasoning_output": state["reasoning_output"],
        "recommendation_output": state["recommendation_output"],
    })
    
    return {
        "explanation_output": out,
        "evidence": out.get("evidence", []),
        "confidence": out.get("computed_confidence", {}),
    }


def human_approval_node(state: PlatformState) -> dict:
    """Human-in-the-loop checkpoint. The graph pauses before entering this node."""
    logger.info("PlannerAgent: human approval node entered/resumed.")
    return {}


def learning_node(state: PlatformState) -> dict:
    """Commit human outcome decision and run reflective learning."""
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
