import logging
import uuid
from typing import Dict, Any, List, Optional
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct, PointIdsList
from qdrant_client.http import models
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from backend.core.settings import settings
from backend.vectorstores.base import BaseVectorStore

logger = logging.getLogger(__name__)

class QdrantStore(BaseVectorStore):
    def __init__(self):
        if settings.QDRANT_URL:
            self._client = QdrantClient(
                url=settings.QDRANT_URL,
                api_key=settings.QDRANT_API_KEY or None,
            )
            logger.info(f"Qdrant client initialized using URL: {settings.QDRANT_URL}")
        else:
            self._client = QdrantClient(path=settings.QDRANT_PATH)
            logger.info(f"Qdrant client initialized locally using path: {settings.QDRANT_PATH}")

        self._embedding_fn = SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2",
        )

    def _collection_name(self, domain_pack_id: str) -> str:
        return f"{settings.MEMORY_COLLECTION_PREFIX}{domain_pack_id}"

    def _get_collection(self, domain_pack_id: str) -> str:
        col_name = self._collection_name(domain_pack_id)
        # Ensure collection exists in Qdrant with correct vector size (all-MiniLM-L6-v2 is 384 dimensions)
        if not self._client.collection_exists(collection_name=col_name):
            logger.info(f"Creating Qdrant collection: {col_name}")
            self._client.create_collection(
                collection_name=col_name,
                vectors_config=VectorParams(size=384, distance=Distance.COSINE),
            )
        return col_name

    def _uuid_from_id(self, doc_id: str) -> str:
        """Deterministically map any string ID to a UUID string for Qdrant compatibility."""
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, doc_id))

    def add_documents(self, domain_pack_id: str, docs: List[Dict[str, Any]]) -> int:
        if not docs:
            return 0
        col_name = self._get_collection(domain_pack_id)
        
        ids = [d["id"] for d in docs]
        documents = [d["content"] for d in docs]
        
        # Generate embeddings using the sentence transformer function
        embeddings = self._embedding_fn(documents)
        
        points = []
        for i, doc in enumerate(docs):
            doc_id = doc["id"]
            uuid_str = self._uuid_from_id(doc_id)
            points.append(
                PointStruct(
                    id=uuid_str,
                    vector=embeddings[i],
                    payload={
                        "_id": doc_id,  # Save the original string ID in payload
                        "content": doc["content"],
                        "metadata": doc.get("metadata") or {"_id": doc_id}
                    }
                )
            )
        
        self._client.upsert(
            collection_name=col_name,
            points=points
        )
        return len(ids)

    def query(self, domain_pack_id: str, query_text: str, k: int = 3) -> List[Dict[str, Any]]:
        col_name = self._get_collection(domain_pack_id)
        
        # Verify collection isn't empty (Qdrant retrieve count)
        stat = self._client.get_collection(collection_name=col_name)
        points_count = stat.points_count if stat.points_count is not None else 0
        if points_count == 0:
            return []

        # Get embedding for search text
        query_vector = self._embedding_fn([query_text])[0]
        
        # Search Qdrant
        results = self._client.query_points(
            collection_name=col_name,
            query=query_vector,
            limit=min(k, points_count),
            with_payload=True
        )

        output: List[Dict[str, Any]] = []
        for hit in results.points:
            payload = hit.payload or {}
            # Restore the original string ID from payload
            output.append({
                "id": payload.get("_id", hit.id),
                "content": payload.get("content", ""),
                "metadata": payload.get("metadata", {}),
                "distance": hit.score if hit.score is not None else None,
            })
        return output

    def delete(self, domain_pack_id: str, document_ids: List[str]) -> bool:
        if not document_ids:
            return False
        col_name = self._get_collection(domain_pack_id)
        
        # Convert IDs to their UUIDv5 counterparts
        uuid_ids = [self._uuid_from_id(doc_id) for doc_id in document_ids]
        try:
            self._client.delete(
                collection_name=col_name,
                points_selector=PointIdsList(points=uuid_ids)
            )
            return True
        except Exception as e:
            logger.error(f"Failed to delete documents from Qdrant: {e}")
            return False

    def clear_collection(self, domain_pack_id: str) -> bool:
        col_name = self._collection_name(domain_pack_id)
        try:
            if self._client.collection_exists(collection_name=col_name):
                self._client.delete_collection(collection_name=col_name)
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to clear Qdrant collection {col_name}: {e}")
            return False

    def get_document_by_id(self, domain_pack_id: str, doc_id: str) -> Optional[Dict[str, Any]]:
        col_name = self._get_collection(domain_pack_id)
        uuid_str = self._uuid_from_id(doc_id)
        try:
            res = self._client.retrieve(
                collection_name=col_name,
                ids=[uuid_str],
                with_payload=True
            )
            if res:
                point = res[0]
                payload = point.payload or {}
                return {
                    "id": doc_id,
                    "content": payload.get("content", ""),
                    "metadata": payload.get("metadata", {}),
                    "distance": 0.80,
                }
        except Exception as e:
            logger.error(f"Failed to retrieve document {doc_id} from Qdrant: {e}")
        return None

    def is_healthy(self) -> bool:
        try:
            self._client.get_collections()
            return True
        except Exception as e:
            logger.error(f"Qdrant client health check failed: {e}")
            return False
