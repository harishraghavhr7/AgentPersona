"""
Backward-compatibility alias for models package.
"""
from .metadata import DocumentMetadata, ChunkPayload, DocumentStatus, SourceType
from .document import NormalizedDocument
from .query import QueryType, ParsedQuery, SourceCitation, QueryResponse, QueryRequest

__all__ = [
    "DocumentMetadata",
    "ChunkPayload",
    "DocumentStatus",
    "SourceType",
    "NormalizedDocument",
    "QueryType",
    "ParsedQuery",
    "SourceCitation",
    "QueryResponse",
    "QueryRequest",
]
