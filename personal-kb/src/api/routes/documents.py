from typing import List
from fastapi import APIRouter, HTTPException
from qdrant_client.http.models import Filter, FieldCondition, MatchValue

from api.schemas import DocumentInfo
from config.settings import get_settings
from ingestion.deduplication import ManifestManager
from storage.qdrant import get_qdrant_client

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.get("", response_model=List[DocumentInfo])
def list_documents():
    manifest = ManifestManager()
    docs = []
    for doc_id, meta in manifest.state.items():
        docs.append(
            DocumentInfo(
                document_id=doc_id,
                source=meta.get("source", ""),
                version=meta.get("version", 1),
                status=meta.get("status", "unknown"),
                content_hash=meta.get("content_hash", ""),
                chunk_ids=meta.get("chunk_ids", []),
                last_ingested_at=meta.get("last_ingested_at"),
            )
        )
    return docs


@router.get("/{document_id}", response_model=DocumentInfo)
def get_document(document_id: str):
    manifest = ManifestManager()
    if document_id not in manifest.state:
        raise HTTPException(status_code=404, detail="Document not found")
    meta = manifest.state[document_id]
    return DocumentInfo(
        document_id=document_id,
        source=meta.get("source", ""),
        version=meta.get("version", 1),
        status=meta.get("status", "unknown"),
        content_hash=meta.get("content_hash", ""),
        chunk_ids=meta.get("chunk_ids", []),
        last_ingested_at=meta.get("last_ingested_at"),
    )


@router.get("/{document_id}/history")
def get_document_history(document_id: str):
    manifest = ManifestManager()
    if document_id not in manifest.state:
        raise HTTPException(status_code=404, detail="Document not found")

    settings = get_settings()
    client = get_qdrant_client()
    raw_coll = settings.qdrant_collection
    coll_name = (raw_coll or "").strip().strip('"').strip("'") or "personal_knowledge"

    points, _ = client.scroll(
        collection_name=coll_name,
        scroll_filter=Filter(must=[FieldCondition(key="document_id", match=MatchValue(value=document_id))]),
        limit=100,
        with_payload=True,
    )

    history = []
    for p in points:
        payload = p.payload or {}
        history.append({
            "point_id": p.id,
            "chunk_id": payload.get("chunk_id"),
            "version": payload.get("version"),
            "status": payload.get("status"),
            "event_at": payload.get("event_at"),
            "valid_from": payload.get("valid_from"),
            "valid_until": payload.get("valid_until"),
            "text_snippet": (payload.get("text") or payload.get("_node_content", ""))[:200],
        })

    def sort_key(item):
        return (item.get("event_at") or "", item.get("valid_from") or "")

    history.sort(key=sort_key)
    return {
        "document_id": document_id,
        "source": manifest.state[document_id].get("source"),
        "total_versions": len(history),
        "timeline": history,
    }
