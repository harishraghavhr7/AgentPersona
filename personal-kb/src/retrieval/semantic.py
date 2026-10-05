import logging
from typing import List, Optional
from qdrant_client import QdrantClient
from qdrant_client.http.models import Filter, ScoredPoint

from config.settings import get_settings
from ingestion.pipeline import get_embedding_model
from storage.qdrant import get_qdrant_client, ensure_collection_and_indexes

logger = logging.getLogger(__name__)


class SemanticRetriever:
    """
    Executes dense semantic vector search against Qdrant using Ollama embeddings.
    """

    def __init__(self, client: Optional[QdrantClient] = None, collection_name: Optional[str] = None):
        self.settings = get_settings()
        self.client = client or get_qdrant_client()
        self.collection_name = collection_name or self.settings.qdrant_collection
        self.embed_model = get_embedding_model()
        ensure_collection_and_indexes(self.client, self.collection_name)

    def search(
        self,
        query_text: str,
        query_filter: Optional[Filter] = None,
        top_k: Optional[int] = None,
    ) -> List[ScoredPoint]:
        k = top_k or self.settings.top_k
        query_vector = self.embed_model.get_query_embedding(query_text)
        
        try:
            response = self.client.query_points(
                collection_name=self.collection_name,
                query=query_vector,
                query_filter=query_filter,
                limit=k,
                with_payload=True,
            )
            return response.points
        except Exception as e:
            logger.warning(f"Error querying collection '{self.collection_name}': {e}")
            return []
