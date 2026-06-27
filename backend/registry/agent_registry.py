"""
Agent Registry — global registry of agent implementations.

Supports registration by name with description, capabilities, and
an optional callable agent instance.
"""

from typing import Dict, Any, List, Optional


# Global registry storage for agents
_agents: Dict[str, Dict[str, Any]] = {}


def register_agent(
    name: str,
    agent: Any,
    description: str,
    capabilities: Optional[List[str]] = None,
) -> None:
    """
    Register an agent with its metadata in the global registry.
    """
    _agents[name] = {
        "name": name,
        "agent": agent,
        "description": description,
        "capabilities": capabilities or [],
    }


def get_agent(name: str) -> Dict[str, Any]:
    """
    Retrieve a registered agent by name.

    Raises KeyError if the agent is not registered.
    """
    if name not in _agents:
        raise KeyError(f"Agent '{name}' is not registered in the Agent Registry.")
    return _agents[name]


def list_agents() -> List[Dict[str, Any]]:
    """
    List metadata for all registered agents.
    """
    return list(_agents.values())


# ---------------------------------------------------------------------------
# Bootstrap — register all built-in agents
# ---------------------------------------------------------------------------


def bootstrap_agents() -> None:
    """
    Register all built-in platform agents.

    Call once at application startup.
    """
    from backend.agents.context_agent import ContextAgent

    ctx = ContextAgent()
    register_agent(
        name=ctx.name,
        agent=ctx,
        description=ctx.description,
        capabilities=ctx.capabilities,
    )
