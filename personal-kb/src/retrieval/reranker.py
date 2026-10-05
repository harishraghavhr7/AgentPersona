"""
Reranker module.
To be activated after baseline retrieval measurement.
"""
from typing import List, Optional
from qdrant_client.http.models import ScoredPoint


class Reranker:
    """
    Reranks candidate points retrieved from Qdrant.
    Configurable via settings.rerank_top_k.
    """

    def __init__(self, is_enabled: bool = False):
        self.is_enabled = is_enabled

    def rerank(self, query: str, candidates: List[ScoredPoint], top_k: int = 3) -> List[ScoredPoint]:
        if not self.is_enabled:
            return candidates[:top_k]
        return candidates[:top_k]
