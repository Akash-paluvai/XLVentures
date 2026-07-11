from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class BaseVectorStore(ABC):
    @abstractmethod
    def add_documents(self, domain_pack_id: str, docs: List[Dict[str, Any]]) -> int:
        """
        Upsert documents into the domain's vector collection.
        Returns the number of documents upserted.
        """
        pass

    @abstractmethod
    def query(
        self, domain_pack_id: str, query_text: str, k: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Query the domain's collection for the k most relevant documents.
        Returns a list of dicts with keys: id, content, metadata, distance.
        """
        pass

    @abstractmethod
    def delete(self, domain_pack_id: str, document_ids: List[str]) -> bool:
        """
        Delete specific documents by their IDs from the domain's collection.
        Returns True if successful, False otherwise.
        """
        pass

    @abstractmethod
    def clear_collection(self, domain_pack_id: str) -> bool:
        """
        Delete the entire collection for a domain.
        Returns True if successful, False otherwise.
        """
        pass

    @abstractmethod
    def get_document_by_id(
        self, domain_pack_id: str, doc_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve a specific document by its ID.
        Returns None if not found.
        """
        pass

    @abstractmethod
    def is_healthy(self) -> bool:
        """
        Check connection health to the vector database.
        Returns True if healthy, False otherwise.
        """
        pass
