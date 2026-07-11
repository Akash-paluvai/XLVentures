"""
Semantic Memory — Unified entrypoint delegating to the configured vector store backend.
"""

from typing import Any, Dict, List

from backend.vectorstores.factory import get_vector_store


def add_documents(domain_pack_id: str, docs: List[Dict[str, Any]]) -> int:
    """Upsert documents into the domain's vector collection."""
    return get_vector_store().add_documents(domain_pack_id, docs)


def query(domain_pack_id: str, query_text: str, k: int = 3) -> List[Dict[str, Any]]:
    """Query the domain's collection for the k most relevant documents."""
    return get_vector_store().query(domain_pack_id, query_text, k)


def delete(domain_pack_id: str, document_ids: List[str]) -> bool:
    """Delete specific documents by their IDs from the domain's collection."""
    return get_vector_store().delete(domain_pack_id, document_ids)


def clear_collection(domain_pack_id: str) -> bool:
    """Delete the entire collection for a domain."""
    return get_vector_store().clear_collection(domain_pack_id)


def get_document_by_id(domain_pack_id: str, doc_id: str) -> dict:
    """Retrieve a specific document by its ID."""
    return get_vector_store().get_document_by_id(domain_pack_id, doc_id)


def is_healthy() -> bool:
    """Check health connection of the active vector store."""
    return get_vector_store().is_healthy()
