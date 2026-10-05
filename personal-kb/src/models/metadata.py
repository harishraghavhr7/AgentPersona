from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_serializer


class DocumentStatus(str, Enum):
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"
    DRAFT = "draft"


class SourceType(str, Enum):
    NOTE = "note"
    PDF = "pdf"
    EMAIL = "email"
    BOOKMARK = "bookmark"
    HTML = "html"
    TXT = "txt"
    UNKNOWN = "unknown"

    @classmethod
    def from_suffix(cls, suffix: str) -> "SourceType":
        normalized = suffix.lower().lstrip(".")
        mapping = {
            "md": cls.NOTE,
            "markdown": cls.NOTE,
            "txt": cls.TXT,
            "pdf": cls.PDF,
            "eml": cls.EMAIL,
            "msg": cls.EMAIL,
            "html": cls.HTML,
            "htm": cls.HTML,
            "url": cls.BOOKMARK,
            "webloc": cls.BOOKMARK,
        }
        return mapping.get(normalized, cls.UNKNOWN)


def format_rfc3339(dt: Optional[datetime]) -> Optional[str]:
    """Return timezone-aware RFC3339 / UTC string for Qdrant payload filtering."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt.isoformat()


class DocumentMetadata(BaseModel):
    document_id: str = Field(description="Stable document identifier")
    source: str = Field(description="File path or URI")
    source_type: SourceType = Field(default=SourceType.UNKNOWN)
    title: Optional[str] = Field(default=None)
    content_hash: str = Field(description="SHA256 hash of the content")

    # Temporal properties
    event_at: Optional[datetime] = Field(
        default=None,
        description="When the event/decision actually happened (real-world event time)"
    )
    valid_from: Optional[datetime] = Field(
        default=None,
        description="When this knowledge became valid/current"
    )
    valid_until: Optional[datetime] = Field(
        default=None,
        description="When this knowledge ceased being valid (None = currently valid)"
    )
    ingested_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When the system learned about it"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When the record was last modified"
    )

    # Versioning & Status
    version: int = Field(default=1, ge=1)
    status: DocumentStatus = Field(default=DocumentStatus.ACTIVE)

    # Classification
    topic: Optional[str] = Field(default=None)
    tags: List[str] = Field(default_factory=list)

    # Lineage & Relationships
    parent_document_id: Optional[str] = Field(default=None)
    supersedes_document_id: Optional[str] = Field(default=None)

    @field_serializer("event_at", "valid_from", "valid_until", "ingested_at", "updated_at")
    def serialize_datetime(self, dt: Optional[datetime]) -> Optional[str]:
        return format_rfc3339(dt)


class ChunkPayload(BaseModel):
    chunk_id: str
    document_id: str
    chunk_index: int = 0
    text: str = ""
    source: str
    source_type: str
    title: Optional[str] = None
    content_hash: str

    # Temporal
    event_at: Optional[str] = None
    valid_from: Optional[str] = None
    valid_until: Optional[str] = None
    ingested_at: str
    updated_at: str

    # Versioning & Status
    version: int = 1
    status: str = "active"

    # Classification
    topic: Optional[str] = None
    tags: List[str] = Field(default_factory=list)

    # Lineage
    parent_document_id: Optional[str] = None
    supersedes_document_id: Optional[str] = None

    def to_qdrant_payload(self) -> Dict[str, Any]:
        """Convert payload to Qdrant-compliant format (RFC3339 datetime strings, primitives)."""
        data = self.model_dump()
        # Ensure datetimes are formatted string or None (Qdrant accepts RFC3339 strings for datetime index)
        return data
