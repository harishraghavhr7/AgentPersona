"""
Hybrid retrieval module (Dense + Sparse/BM25).
To be enabled after baseline temporal retrieval measurement.
"""
from typing import List, Optional
from qdrant_client.http.models import ScoredPoint, Filter


class HybridRetriever:
    """
    Combines dense semantic vector search with sparse lexical search in Qdrant.
    Activated via configuration when exact keyword matching is required.
    """

    def __init__(self, is_enabled: bool = False):
        self.is_enabled = is_enabled

    def search(
        self,
        query: str,
        query_filter: Optional[Filter] = None,
        top_k: int = 5,
    ) -> List[ScoredPoint]:
        # Baseline fallback until hybrid weights are configured
        return []
