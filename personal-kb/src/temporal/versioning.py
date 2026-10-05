from datetime import datetime, timezone
from typing import List, Optional
from models.metadata import DocumentMetadata, DocumentStatus, format_rfc3339


class VersionManager:
    """
    Manages document versioning, validity windows, and supersession links.
    Ensures that historical knowledge is never deleted, but marked as superseded.
    """

    @staticmethod
    def transition_superseded(
        old_metadata: DocumentMetadata,
        new_metadata: DocumentMetadata,
        supersede_time: Optional[datetime] = None,
    ) -> DocumentMetadata:
        """
        Transitions an old active document to superseded state when a new version or
        decision is published.
        """
        effective_time = supersede_time or new_metadata.valid_from or new_metadata.event_at or datetime.now(timezone.utc)
        
        old_metadata.status = DocumentStatus.SUPERSEDED
        old_metadata.valid_until = effective_time
        old_metadata.updated_at = datetime.now(timezone.utc)

        new_metadata.version = old_metadata.version + 1
        new_metadata.supersedes_document_id = old_metadata.document_id
        new_metadata.valid_from = effective_time
        new_metadata.valid_until = None
        new_metadata.status = DocumentStatus.ACTIVE

        return old_metadata

    @staticmethod
    def sort_chronological(documents: List[DocumentMetadata]) -> List[DocumentMetadata]:
        """Sort documents chronologically by event_at, then valid_from, then ingested_at."""
        def sort_key(d: DocumentMetadata):
            return (
                d.event_at or datetime.min.replace(tzinfo=timezone.utc),
                d.valid_from or datetime.min.replace(tzinfo=timezone.utc),
                d.ingested_at or datetime.min.replace(tzinfo=timezone.utc),
            )
        return sorted(documents, key=sort_key)
