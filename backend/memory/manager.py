"""
Memory Manager — unified retrieval interface for agents.

Orchestrates queries across both episodic (SQLite) and semantic (ChromaDB)
memory layers so downstream agents never interact with storage directly.
"""

import time
from typing import Dict, Any

from backend.memory import episodic, semantic


class MemoryManager:
    """
    Unified memory manager abstraction layer.
    Agents call ``retrieve_context`` and receive a combined payload of
    playbook snippets, historical case data, and retrieval metadata.
    """

    def retrieve_context(self, domain_pack_id: str, query: str) -> Dict[str, Any]:
        """
        Orchestrate retrieval across semantic and episodic memory.

        Returns:
            {
                "playbooks":  [ ... ],
                "past_cases": [ ... ],
                "metadata": {
                    "playbook_count":  int,
                    "past_case_count": int,
                    "latency_ms":      float,
                },
            }
        """
        t0 = time.perf_counter()

        playbooks = semantic.query(domain_pack_id, query, k=3)
        
        # Dynamically retrieve and append learned heuristics if they exist
        learned = semantic.get_document_by_id(domain_pack_id, "learned_heuristics")
        if learned and not any(pb["id"] == "learned_heuristics" for pb in playbooks):
            playbooks.append(learned)

        past_cases = episodic.get_similar_past_cases(domain_pack_id, query, limit=5)

        latency_ms = round((time.perf_counter() - t0) * 1000, 2)

        return {
            "playbooks": playbooks,
            "past_cases": past_cases,
            "metadata": {
                "playbook_count": len(playbooks),
                "past_case_count": len(past_cases),
                "latency_ms": latency_ms,
            },
        }


# Global singleton — importable by agents and API routes.
memory_manager = MemoryManager()
