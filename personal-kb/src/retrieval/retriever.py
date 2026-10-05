"""
Backward-compatibility alias for retrieval module.
"""
from .service import RetrievalService
from .semantic import SemanticRetriever
from .temporal import TemporalRetriever

__all__ = ["RetrievalService", "SemanticRetriever", "TemporalRetriever"]
