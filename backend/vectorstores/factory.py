import logging
from backend.core.settings import settings
from backend.vectorstores.base import BaseVectorStore

logger = logging.getLogger(__name__)

# Single store instance cached globally
_store_instance = None

def get_vector_store() -> BaseVectorStore:
    """
    Get the configured vector store instance based on settings.VECTOR_DB.
    Caches the instance to avoid re-initializing client connections.
    """
    global _store_instance
    if _store_instance is not None:
        return _store_instance

    vector_db_type = settings.VECTOR_DB.lower()
    
    if vector_db_type == "chroma":
        from backend.vectorstores.chroma_store import ChromaStore
        logger.info("Initializing Chroma vector store...")
        _store_instance = ChromaStore()
    elif vector_db_type == "qdrant":
        from backend.vectorstores.qdrant_store import QdrantStore
        logger.info("Initializing Qdrant vector store...")
        _store_instance = QdrantStore()
    else:
        # Fallback to Chroma
        logger.warning(f"Unknown VECTOR_DB config '{settings.VECTOR_DB}'. Falling back to ChromaStore.")
        from backend.vectorstores.chroma_store import ChromaStore
        _store_instance = ChromaStore()

    return _store_instance
