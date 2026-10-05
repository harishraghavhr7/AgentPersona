from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from models.query import Citation, SourceCitation, QueryType, RAGResponse


class HealthResponse(BaseModel):
    status: str
    qdrant_status: str
    ollama_status: str
    collection: str
    active_models: Dict[str, str]
    llm_fallback_chain: Optional[List[str]] = None
    providers_configured: Optional[Dict[str, bool]] = None


class IngestRequest(BaseModel):
    directory_path: Optional[str] = None
    force_reindex: bool = False


class IngestResponse(BaseModel):
    processed: int
    added: int
    updated: int
    skipped: int
    failed: int


class TextIngestRequest(BaseModel):
    text: str
    title: Optional[str] = None
    category: str = "notes"
    filename: Optional[str] = None
    event_at: Optional[str] = None
    append: bool = False


class TextIngestResponse(BaseModel):
    status: str
    document_id: str
    source: str
    filename: str
    chunks_count: int
    version: int
    title: Optional[str] = None
    message: str


class FileIngestRequest(BaseModel):
    filename: str
    content_base64: Optional[str] = None
    content_text: Optional[str] = None
    category: str = "notes"
    force_reindex: bool = False


class FileIngestResponse(BaseModel):
    status: str
    document_id: str
    source: str
    filename: str
    chunks_count: int
    version: int
    title: Optional[str] = None
    message: str


class QueryApiRequest(BaseModel):
    query: str
    top_k: Optional[int] = None
    debug: bool = False


class QueryApiResponse(BaseModel):
    answer: str
    citations: List[Citation] = Field(default_factory=list)
    sources: List[Citation] = Field(default_factory=list)
    query_type: QueryType
    temporal_filter: Optional[Dict[str, Any]] = None
    debug_info: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


class DocumentInfo(BaseModel):
    document_id: str
    source: str
    version: int
    status: str
    content_hash: str
    chunk_ids: List[str]
    last_ingested_at: Optional[str] = None
