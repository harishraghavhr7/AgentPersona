from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class QueryType(str, Enum):
    SEMANTIC = "SEMANTIC"
    TEMPORAL = "TEMPORAL"
    CURRENT_STATE = "CURRENT_STATE"
    HISTORICAL = "HISTORICAL"
    COMPARISON = "COMPARISON"
    SUPERSESSION = "SUPERSESSION"
    SOURCE_LOOKUP = "SOURCE_LOOKUP"


class TemporalType(str, Enum):
    EVENT_TIME = "event_time"
    VALIDITY_TIME = "validity_time"
    INGESTION_TIME = "ingestion_time"


class TemporalRange(BaseModel):
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    temporal_type: TemporalType = TemporalType.EVENT_TIME
    is_point_in_time: bool = False
    target_status: Optional[str] = None  # e.g., "active", "superseded"
    description: Optional[str] = None


class ParsedQuery(BaseModel):
    original_query: str
    semantic_query: str
    query_type: QueryType = QueryType.SEMANTIC
    temporal_range: Optional[TemporalRange] = None
    target_source_type: Optional[str] = None
    target_document_id: Optional[str] = None


class Citation(BaseModel):
    id: int
    source: str
    title: Optional[str] = None
    chunk_id: Optional[str] = None
    score: Optional[float] = None
    snippet: Optional[str] = None
    page: Optional[int] = None
    created_at: Optional[str] = None
    document_type: Optional[str] = None
    status: Optional[str] = None
    event_at: Optional[str] = None
    valid_from: Optional[str] = None
    valid_until: Optional[str] = None
    version: Optional[int] = None
    document_id: Optional[str] = None


# Backward-compatibility alias
SourceCitation = Citation


class QueryRequest(BaseModel):
    query: str
    top_k: Optional[int] = None
    debug: bool = False


class RAGResponse(BaseModel):
    answer: str
    citations: List[Citation] = Field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = None


class QueryResponse(BaseModel):
    answer: str
    citations: List[Citation] = Field(default_factory=list)
    sources: List[Citation] = Field(default_factory=list)
    query_type: QueryType = QueryType.SEMANTIC
    temporal_filter: Optional[Dict[str, Any]] = None
    debug_info: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
