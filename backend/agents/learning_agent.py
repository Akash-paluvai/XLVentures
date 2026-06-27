"""
Learning Agent — writes outcomes to episodic memory (SQLite), and executes
reflection mining to generate and upsert learned heuristics back into
semantic memory (ChromaDB) for continuous learning.
"""

import json
import logging
from typing import Dict, Any, List

from backend.memory.episodic import write_recommendation, write_feedback, SessionLocal, RecommendationRecord, FeedbackRecord
from backend.memory.semantic import add_documents

logger = logging.getLogger(__name__)


class LearningAgent:
    """
    Persists decisions and feedback to episodic memory, and mines patterns for semantic memory writeback.

    Inputs:
        write_outcome inputs:
            domain_pack_id: str
            entity_id: str
            recommendation: dict
            human_feedback: str
            outcome: str

        run_reflection inputs:
            domain_pack_id: str
    """

    name = "learning_agent"
    description = "Logs human outcomes to episodic memory and reflectively writes learned rules back to semantic memory."
    capabilities = ["write_outcome", "run_reflection"]

    def write_outcome(
        self,
        domain_pack_id: str,
        entity_id: str,
        recommendation: Dict[str, Any],
        human_feedback: str,
        outcome: str,
    ) -> str:
        """
        Write the recommendation record and feedback outcome to episodic SQLite memory.
        Returns the generated feedback_id.
        """
        # Step 1: Write recommendation to database
        rec_id = write_recommendation(
            entity_id=entity_id,
            domain_pack_id=domain_pack_id,
            recommendation_dict=recommendation,
        )

        # Step 2: Write feedback outcome to database
        fb_id = write_feedback(
            recommendation_id=rec_id,
            entity_id=entity_id,
            domain_pack_id=domain_pack_id,
            human_feedback=human_feedback,
            outcome=outcome,
        )

        logger.info(f"LearningAgent: Saved outcome to episodic memory (rec_id={rec_id}, fb_id={fb_id}).")
        return fb_id

    def run_reflection(self, domain_pack_id: str) -> Dict[str, Any]:
        """
        Mine episodic memory SQLite for outcomes, identify patterns, and write
        summarized learned heuristics back to ChromaDB semantic memory.
        """
        logger.info(f"LearningAgent: Running reflection job for domain '{domain_pack_id}'.")

        # Step 1: Query all feedback and recommendations for the domain
        try:
            with SessionLocal() as session:
                rows = (
                    session.query(FeedbackRecord, RecommendationRecord)
                    .join(RecommendationRecord, RecommendationRecord.recommendation_id == FeedbackRecord.recommendation_id)
                    .filter(RecommendationRecord.domain_pack_id == domain_pack_id)
                    .all()
                )
        except Exception as e:
            logger.error(f"LearningAgent: Failed to fetch episodic memory records: {e}")
            return {"status": "error", "message": str(e)}

        # Step 2: Aggregate outcomes per selected action title
        stats = {}
        for fb, rec in rows:
            try:
                rec_data = json.loads(rec.recommendation_json)
                selected = rec_data.get("selected_action") or {}
                title = selected.get("title", "Unknown Action")

                if title not in stats:
                    stats[title] = {"approved": 0, "rejected": 0, "edited": 0, "needs_info": 0}

                outcome = fb.outcome  # e.g., 'approved', 'rejected', 'edited', 'needs_info'
                if outcome in stats[title]:
                    stats[title][outcome] += 1
            except Exception as ex:
                logger.warning(f"LearningAgent: Failed to parse recommendation: {ex}")
                continue

        # Step 3: Format the learned heuristics Markdown document
        domain_name = domain_pack_id.replace("_", " ").title()
        markdown = f"# Learned Heuristics for {domain_name}\n\n"
        markdown += (
            "This document summarizes patterns mined from past human approvals and rejections. "
            "These guidelines should influence future context retrieval and decision reasoning:\n\n"
        )

        if stats:
            for title, outcomes in stats.items():
                markdown += f"### Action: {title}\n"
                markdown += f"- Approved Count: {outcomes['approved']}\n"
                markdown += f"- Rejected Count: {outcomes['rejected']}\n"
                markdown += f"- Edited Count: {outcomes['edited']}\n"
                
                # Simple heuristic rule generation
                if outcomes["rejected"] > outcomes["approved"]:
                    markdown += f"- **Guidance**: High risk of rejection. Human success managers frequently reject this action. Reconsider selecting it as the primary next best action unless no other options are feasible.\n"
                else:
                    markdown += f"- **Guidance**: Strong human acceptance. This action is highly favored and should be prioritized when context aligns.\n"
                markdown += "\n"
        else:
            markdown += "No human feedback outcomes registered yet. Default playbook guidelines apply.\n"

        # Step 4: Write/upsert the learned heuristics document into ChromaDB
        try:
            docs = [
                {
                    "id": "learned_heuristics",
                    "content": markdown,
                    "metadata": {
                        "type": "playbook",
                        "domain": domain_pack_id,
                        "filename": "learned_heuristics.md",
                    },
                }
            ]
            add_documents(domain_pack_id, docs)
            logger.info("LearningAgent: Successfully updated 'learned_heuristics' in semantic memory.")
        except Exception as e:
            logger.error(f"LearningAgent: Failed to write learned heuristics to ChromaDB: {e}")
            return {"status": "error", "message": str(e)}

        return {
            "status": "success",
            "domain_pack_id": domain_pack_id,
            "feedback_records_analyzed": len(rows),
            "aggregated_heuristics": stats,
            "heuristics_document": markdown,
        }
