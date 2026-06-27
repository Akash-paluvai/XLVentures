import logging
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from backend.core.settings import settings
from backend.core.config_loader import load_domain_pack, load_accounts

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api")

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="FastAPI backend for Agentic Decision Intelligence Platform - Shift 1 V1"
)

# CORS configuration from settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


from pydantic import BaseModel
from typing import Optional, Dict, Any
import uuid

from backend.registry.agent_registry import bootstrap_agents, get_agent
from backend.core.planner import graph

# Request schemas
class RecommendRequest(BaseModel):
    domain_pack_id: str
    entity_id: str
    interaction: Optional[str] = None

class ApproveRequest(BaseModel):
    thread_id: str
    outcome: str
    feedback_text: Optional[str] = None
    edited_action: Optional[Dict[str, Any]] = None


@app.on_event("startup")
def startup_event():
    """
    On startup, load and validate all available domain packs,
    and bootstrap all built-in agents.
    """
    logger.info("Initializing and validating domain packs...")
    packs_to_validate = ["customer_success", "recruitment"]
    
    for pack_name in packs_to_validate:
        try:
            load_domain_pack(pack_name)
            logger.info(f"Successfully validated domain pack: '{pack_name}' schema matches core contract.")
        except Exception as e:
            logger.error(f"CRITICAL: Failed to validate domain pack '{pack_name}': {str(e)}")
            raise RuntimeError(f"Startup check failed: Domain pack '{pack_name}' is invalid. Reason: {str(e)}")
            
    logger.info("Bootstrapping agents in registry...")
    bootstrap_agents()


@app.get(f"{settings.API_V1_PREFIX}/health")
def get_health():
    """
    Returns API health status.
    """
    return {"status": "healthy"}


@app.get(f"{settings.API_V1_PREFIX}/domain")
def get_domain(domain: str = Query("customer_success", description="The domain pack identifier to load")):
    """
    Loads and returns a validated domain pack configuration.
    """
    try:
        data = load_domain_pack(domain)
        return data
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Invalid configuration or validation failure: {str(e)}")


@app.get(f"{settings.API_V1_PREFIX}/accounts")
def get_accounts(domain: str = Query("customer_success", description="The domain name to load accounts/candidates for")):
    """
    Loads and returns accounts or candidates list for the requested domain pack.
    """
    try:
        data = load_accounts(domain)
        return data
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")


@app.post(f"{settings.API_V1_PREFIX}/recommend")
def post_recommend(req: RecommendRequest):
    """
    Kicks off the decision intelligence pipeline for the given entity.
    Runs until the human approval gate (interrupt), returning the intermediate recommendation.
    """
    try:
        domain_pack = load_domain_pack(req.domain_pack_id)
        entities = load_accounts(req.domain_pack_id)
        
        # Find matching account/candidate
        id_key = "account_id" if req.domain_pack_id == "customer_success" else "candidate_id"
        entity = next((e for e in entities if e.get(id_key) == req.entity_id), None)
        
        if not entity:
            raise HTTPException(status_code=404, detail=f"Entity with ID '{req.entity_id}' not found in domain '{req.domain_pack_id}'.")
            
        interaction_text = req.interaction if req.interaction else entity.get("interaction_notes") or entity.get("recruiter_notes") or ""
        
        # Initialize graph state
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
        
        # Run graph up to the interrupt
        logger.info(f"API: Running graph on thread '{thread_id}' for entity '{req.entity_id}'...")
        for event in graph.stream(state, config):
            pass
            
        # Get compiled output at the checkpoint
        checkpoint_state = graph.get_state(config)
        
        return {
            "thread_id": thread_id,
            "recommendation": checkpoint_state.values.get("explanation_output"),
            "routing_path": checkpoint_state.values.get("metadata", {}).get("routing_path"),
            "status": "paused_for_approval"
        }
        
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error executing recommendation: {e}")
        raise HTTPException(status_code=500, detail=f"Graph execution failure: {str(e)}")


@app.post(f"{settings.API_V1_PREFIX}/approve")
def post_approve(req: ApproveRequest):
    """
    Submits human feedback for the paused thread, resuming execution to log outcomes.
    """
    try:
        config = {"configurable": {"thread_id": req.thread_id}}
        current_state = graph.get_state(config)
        
        if not current_state.values:
            raise HTTPException(status_code=404, detail=f"Thread '{req.thread_id}' not found or has already expired.")
            
        # Prepare state updates
        state_updates = {
            "human_feedback": {
                "outcome": req.outcome,
                "feedback_text": req.feedback_text
            }
        }
        
        # If human edited the selected action, override explanation payload
        if req.outcome == "edited" and req.edited_action:
            explanation_output = current_state.values.get("explanation_output")
            if explanation_output:
                explanation_output["selected_action"] = req.edited_action
                state_updates["explanation_output"] = explanation_output
                
        # Resume the graph by updating the state and signaling run
        logger.info(f"API: Resuming graph on thread '{req.thread_id}' with outcome '{req.outcome}'...")
        graph.update_state(config, state_updates, as_node="human_approval_node")
        
        for event in graph.stream(None, config):
            pass
            
        final_state = graph.get_state(config)
        return {
            "status": "success",
            "metadata": final_state.values.get("metadata"),
            "outcome": req.outcome
        }
        
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error resuming recommendation thread '{req.thread_id}': {e}")
        raise HTTPException(status_code=500, detail=f"Resumption execution failure: {str(e)}")


class ReflectRequest(BaseModel):
    domain_pack_id: str


@app.post(f"{settings.API_V1_PREFIX}/reflect")
def post_reflect(req: ReflectRequest):
    """
    Manually triggers the Learning Agent's reflection logic to analyze feedback
    in episodic SQLite memory and upsert learned heuristics back into semantic ChromaDB.
    """
    try:
        agent = get_agent("learning_agent")["agent"]
        result = agent.run_reflection(req.domain_pack_id)
        return result
    except Exception as e:
        logger.error(f"Error executing manual reflection for '{req.domain_pack_id}': {e}")
        raise HTTPException(status_code=500, detail=f"Reflection execution failure: {str(e)}")


