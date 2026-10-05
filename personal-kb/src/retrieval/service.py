import json
from datetime import datetime
from typing import List, Optional, Tuple
from qdrant_client.http.models import Filter, ScoredPoint

import os
from pathlib import Path
from models.query import ParsedQuery, Citation, SourceCitation
from .temporal import TemporalRetriever


class RetrievalService:
    """
    High-level retrieval service.
    Orchestrates query parsing, vector retrieval with temporal filtering,
    payload decoding, snippet extraction, and citation building.
    """

    def __init__(self, temporal_retriever: Optional[TemporalRetriever] = None):
        self.retriever = temporal_retriever or TemporalRetriever()

    def retrieve_context(
        self,
        query: str,
        top_k: Optional[int] = None,
        reference_date: Optional[datetime] = None,
    ) -> Tuple[str, List[Citation], ParsedQuery, Optional[Filter]]:
        points, parsed_query, qdrant_filter = self.retriever.retrieve(
            query=query,
            top_k=top_k,
            reference_date=reference_date,
        )

        citations: List[Citation] = []
        context_blocks: List[str] = []

        for idx, pt in enumerate(points):
            citation_id = idx + 1
            payload = pt.payload or {}
            
            # Extract text from LlamaIndex node content or payload
            text = payload.get("text", "")
            if not text and "_node_content" in payload:
                try:
                    node_data = json.loads(payload["_node_content"])
                    text = node_data.get("text", "")
                except Exception:
                    text = ""

            doc_id = payload.get("document_id", "unknown")
            chunk_id = payload.get("chunk_id", str(pt.id))
            raw_source = payload.get("source", "unknown")
            
            # Normalize to clean filename
            source = os.path.basename(raw_source.replace("\\", "/"))

            # Derive title: from payload -> first markdown heading -> filename stem
            title = payload.get("title")
            if not title:
                for line in text.splitlines():
                    clean_line = line.strip()
                    if clean_line.startswith("#"):
                        title = clean_line.lstrip("#").strip()
                        break
            if not title:
                title = Path(source).stem.replace("_", " ").replace("-", " ").title()

            event_at = payload.get("event_at")
            valid_from = payload.get("valid_from")
            valid_until = payload.get("valid_until")
            status = payload.get("status", "active")
            version = payload.get("version")
            source_type = payload.get("source_type") or ("decision" if "decision" in source.lower() else "note")
            created_at = event_at or payload.get("ingested_at")

            citation = Citation(
                id=citation_id,
                source=source,
                title=title,
                chunk_id=chunk_id,
                score=round(pt.score, 4) if pt.score is not None else None,
                snippet=text[:300].strip(),
                created_at=created_at,
                document_type=source_type,
                status=status,
                event_at=event_at,
                valid_from=valid_from,
                valid_until=valid_until,
                version=version,
                document_id=doc_id,
            )
            citations.append(citation)

            # Build grounded context block with numbered citation marker [1], [2]
            date_info = f"Event Date: {event_at}" if event_at else "Date: Not specified"
            valid_info = f"Status: {status.upper() if status else 'ACTIVE'} (Valid from {valid_from or 'start'} to {valid_until or 'present'})"
            block = (
                f"[{citation_id}] Source: {source} (Title: {title}) | {valid_info} | {date_info}\n"
                f"{text}\n"
            )
            context_blocks.append(block)

        combined_context = "\n".join(context_blocks)
        return combined_context, citations, parsed_query, qdrant_filter
