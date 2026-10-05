import re
import uuid
from datetime import datetime, timezone
from typing import List, Optional
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import TextNode, Document, NodeRelationship, RelatedNodeInfo

from models.metadata import format_rfc3339
from temporal.parser import extract_event_date_from_text


def generate_chunk_uuid(chunk_id: str) -> str:
    """Generate deterministic UUID for Qdrant point compatibility."""
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, chunk_id))


def parse_document_into_chunks(
    document: Document,
    document_id: str,
    source: str,
    source_type: str,
    content_hash: str,
    title: Optional[str] = None,
    chunk_size: int = 512,
    chunk_overlap: int = 50,
) -> List[TextNode]:
    """
    Parse a document into TextNode objects with temporal boundaries and metadata.
    Preserves decision timeline and distinct dated blocks.
    """
    raw_text = document.text.replace("\r\n", "\n").replace("\r", "\n").strip()
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", raw_text) if p.strip()]

    # Inspect paragraphs for dates
    dated_entries = []
    header_prefix = ""
    current_entry_lines = []
    current_date = None

    for p in paragraphs:
        # Check if it's a top-level header without date
        if p.startswith("#") and extract_event_date_from_text(p) is None:
            if not header_prefix:
                header_prefix = p + "\n\n"
            continue

        p_date = extract_event_date_from_text(p)
        if p_date is not None:
            if current_entry_lines:
                dated_entries.append((current_date, "\n\n".join(current_entry_lines)))
                current_entry_lines = []
            current_date = p_date
            current_entry_lines.append(p)
        else:
            current_entry_lines.append(p)

    if current_entry_lines:
        dated_entries.append((current_date, "\n\n".join(current_entry_lines)))

    now = datetime.now(timezone.utc)
    now_rfc = format_rfc3339(now)
    nodes: List[TextNode] = []

    if len(dated_entries) > 1 and all(d is not None for d, _ in dated_entries):
        # Multi-decision / multi-date timeline document
        dated_entries.sort(key=lambda x: x[0])
        total = len(dated_entries)

        for idx, (entry_date, entry_text) in enumerate(dated_entries):
            full_text = f"{header_prefix}{entry_text}".strip()
            
            valid_from = entry_date
            if idx < total - 1:
                next_date = dated_entries[idx + 1][0]
                valid_until = next_date
                status = "superseded"
            else:
                valid_until = None
                status = "active"

            chunk_id = f"{document_id}__c{idx}"
            node_id = generate_chunk_uuid(chunk_id)

            node = TextNode(
                text=full_text,
                id_=node_id,
                metadata={
                    "document_id": document_id,
                    "chunk_id": chunk_id,
                    "point_id": node_id,
                    "chunk_index": idx,
                    "source": source,
                    "source_type": source_type,
                    "title": title or "",
                    "content_hash": content_hash,
                    "event_at": format_rfc3339(entry_date),
                    "valid_from": format_rfc3339(valid_from),
                    "valid_until": format_rfc3339(valid_until),
                    "ingested_at": now_rfc,
                    "updated_at": now_rfc,
                    "status": status,
                    "version": 1,
                },
            )
            node.relationships[NodeRelationship.SOURCE] = RelatedNodeInfo(node_id=document_id)
            nodes.append(node)
    else:
        # Standard document: split using SentenceSplitter
        splitter = SentenceSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
        sub_docs = splitter.split_text(raw_text)
        doc_date = extract_event_date_from_text(raw_text)

        for idx, chunk_text in enumerate(sub_docs):
            chunk_date = extract_event_date_from_text(chunk_text) or doc_date
            chunk_id = f"{document_id}__c{idx}"
            node_id = generate_chunk_uuid(chunk_id)

            node = TextNode(
                text=chunk_text,
                id_=node_id,
                metadata={
                    "document_id": document_id,
                    "chunk_id": chunk_id,
                    "point_id": node_id,
                    "chunk_index": idx,
                    "source": source,
                    "source_type": source_type,
                    "title": title or "",
                    "content_hash": content_hash,
                    "event_at": format_rfc3339(chunk_date),
                    "valid_from": format_rfc3339(chunk_date or now),
                    "valid_until": None,
                    "ingested_at": now_rfc,
                    "updated_at": now_rfc,
                    "status": "active",
                    "version": 1,
                },
            )
            node.relationships[NodeRelationship.SOURCE] = RelatedNodeInfo(node_id=document_id)
            nodes.append(node)

    return nodes
