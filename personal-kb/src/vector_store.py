"""
Backward-compatibility adapter for vector store.
Delegates to storage.qdrant.
"""
from storage.qdrant import get_qdrant_client, get_vector_store

__all__ = ["get_qdrant_client", "get_vector_store"]