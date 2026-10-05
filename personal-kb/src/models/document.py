from datetime import datetime, timezone
import hashlib
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel, Field

from .metadata import DocumentMetadata, DocumentStatus, SourceType, format_rfc3339


def compute_content_hash(text: str) -> str:
    """Compute deterministic SHA-256 hash of text content."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def generate_stable_document_id(source_path: str) -> str:
    """Generate deterministic document_id based on normalized relative source path."""
    normalized_path = Path(source_path).as_posix().lower()
    return hashlib.sha256(normalized_path.encode("utf-8")).hexdigest()[:16]


class NormalizedDocument(BaseModel):
    document_id: str
    text: str
    metadata: DocumentMetadata
    raw_content: Optional[str] = None

    @classmethod
    def from_text_and_source(
        cls,
        text: str,
        source: str,
        title: Optional[str] = None,
        source_type: Optional[SourceType] = None,
        event_at: Optional[datetime] = None,
        valid_from: Optional[datetime] = None,
        valid_until: Optional[datetime] = None,
        version: int = 1,
        status: DocumentStatus = DocumentStatus.ACTIVE,
        topic: Optional[str] = None,
        tags: Optional[List[str]] = None,
        parent_document_id: Optional[str] = None,
        supersedes_document_id: Optional[str] = None,
    ) -> "NormalizedDocument":
        doc_id = generate_stable_document_id(source)
        content_hash = compute_content_hash(text)
        src_type = source_type or SourceType.from_suffix(Path(source).suffix)
        now = datetime.now(timezone.utc)

        meta = DocumentMetadata(
            document_id=doc_id,
            source=source,
            source_type=src_type,
            title=title or Path(source).stem.replace("_", " ").title(),
            content_hash=content_hash,
            event_at=event_at,
            valid_from=valid_from,
            valid_until=valid_until,
            ingested_at=now,
            updated_at=now,
            version=version,
            status=status,
            topic=topic,
            tags=tags or [],
            parent_document_id=parent_document_id,
            supersedes_document_id=supersedes_document_id,
        )
        return cls(
            document_id=doc_id,
            text=text,
            metadata=meta,
        )
