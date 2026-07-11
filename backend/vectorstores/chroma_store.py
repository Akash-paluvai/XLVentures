import logging
from typing import Any, Dict, List, Optional

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

from backend.core.settings import settings
from backend.vectorstores.base import BaseVectorStore

logger = logging.getLogger(__name__)


class ChromaStore(BaseVectorStore):
    def __init__(self):
        self._client = chromadb.PersistentClient(path=settings.CHROMA_PATH)
        self._embedding_fn: Any = SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2",
        )

    def _collection_name(self, domain_pack_id: str) -> str:
        return f"{settings.MEMORY_COLLECTION_PREFIX}{domain_pack_id}"

    def _get_collection(self, domain_pack_id: str):
        return self._client.get_or_create_collection(
            name=self._collection_name(domain_pack_id),
            embedding_function=self._embedding_fn,
        )

    def add_documents(self, domain_pack_id: str, docs: List[Dict[str, Any]]) -> int:
        if not docs:
            return 0
        collection = self._get_collection(domain_pack_id)
        ids = [d["id"] for d in docs]
        documents = [d["content"] for d in docs]
        metadatas = [d.get("metadata") or {"_id": d["id"]} for d in docs]

        collection.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
        )
        return len(ids)

    def query(
        self, domain_pack_id: str, query_text: str, k: int = 3
    ) -> List[Dict[str, Any]]:
        collection = self._get_collection(domain_pack_id)
        if collection.count() == 0:
            return []

        results = collection.query(
            query_texts=[query_text],
            n_results=min(k, collection.count()),
        )

        ids = results.get("ids")
        if not ids or not ids[0]:
            return []

        documents = results.get("documents") or []
        metadatas = results.get("metadatas") or []
        distances = results.get("distances") or []

        output: List[Dict[str, Any]] = []
        for i in range(len(ids[0])):
            output.append(
                {
                    "id": ids[0][i],
                    "content": (
                        documents[0][i]
                        if (documents and len(documents) > 0 and len(documents[0]) > i)
                        else ""
                    ),
                    "metadata": (
                        metadatas[0][i]
                        if (
                            metadatas
                            and len(metadatas) > 0
                            and len(metadatas[0]) > i
                            and metadatas[0]
                        )
                        else {}
                    ),
                    "distance": (
                        distances[0][i]
                        if (
                            distances
                            and len(distances) > 0
                            and len(distances[0]) > i
                            and distances[0]
                        )
                        else None
                    ),
                }
            )
        return output

    def delete(self, domain_pack_id: str, document_ids: List[str]) -> bool:
        if not document_ids:
            return False
        collection = self._get_collection(domain_pack_id)
        try:
            collection.delete(ids=document_ids)
            return True
        except Exception as e:
            logger.error(f"Failed to delete documents from Chroma: {e}")
            return False

    def clear_collection(self, domain_pack_id: str) -> bool:
        col_name = self._collection_name(domain_pack_id)
        try:
            self._client.delete_collection(name=col_name)
            return True
        except ValueError:
            return False

    def get_document_by_id(
        self, domain_pack_id: str, doc_id: str
    ) -> Optional[Dict[str, Any]]:
        collection = self._get_collection(domain_pack_id)
        try:
            res = collection.get(ids=[doc_id])
            if res and res.get("documents") and len(res["documents"]) > 0:
                return {
                    "id": doc_id,
                    "content": res["documents"][0],
                    "metadata": res["metadatas"][0] if res["metadatas"] else {},
                    "distance": 0.80,
                }
        except Exception:
            pass
        return None

    def is_healthy(self) -> bool:
        try:
            self._client.heartbeat()
            return True
        except Exception as e:
            logger.error(f"Chroma client health check failed: {e}")
            return False
