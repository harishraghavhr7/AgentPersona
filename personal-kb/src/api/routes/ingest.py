import base64
import logging
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from api.schemas import (
    FileIngestRequest,
    FileIngestResponse,
    IngestRequest,
    IngestResponse,
    TextIngestRequest,
    TextIngestResponse,
)
from config.settings import get_settings
from ingestion.service import IngestionService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Ingestion"])


@router.post("/ingest", response_model=IngestResponse)
def ingest_documents(payload: IngestRequest):
    """Scan and ingest all documents from a directory (idempotent, temporal change detection)."""
    try:
        service = IngestionService()
        result = service.ingest_directory(
            directory_path=payload.directory_path,
            force_reindex=payload.force_reindex,
        )
        return IngestResponse(**result)
    except Exception as e:
        logger.error(f"Error during directory ingestion: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ingest/text", response_model=TextIngestResponse)
def ingest_text_note(payload: TextIngestRequest):
    """
    Ingest text notes directly (e.g. current accomplishments, project rules, decisions).
    Saves the content to disk and immediately embeds and indexes it into Qdrant.
    """
    try:
        if not payload.text or not payload.text.strip():
            raise HTTPException(status_code=400, detail="Text content cannot be empty.")

        service = IngestionService()
        result = service.ingest_text(
            text=payload.text,
            title=payload.title,
            category=payload.category,
            source_name=payload.filename,
            event_at=payload.event_at,
            append=payload.append,
        )
        return TextIngestResponse(
            status=result["status"],
            document_id=result["document_id"],
            source=result["source"],
            filename=result["filename"],
            chunks_count=result["chunks_count"],
            version=result["version"],
            title=result.get("title"),
            message=f"Successfully indexed '{result['filename']}' ({result['chunks_count']} chunk(s), status: {result['status']}).",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error ingesting text note: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ingest/file", response_model=FileIngestResponse)
def ingest_file_payload(payload: FileIngestRequest):
    """
    Ingest a document payload (Base64 encoded or raw text) for formats including:
    .doc, .docx, .pdf, .md, .txt.
    """
    try:
        settings = get_settings()
        target_dir = Path(settings.data_dir) / payload.category
        target_dir.mkdir(parents=True, exist_ok=True)

        target_file = target_dir / Path(payload.filename).name

        if payload.content_base64:
            raw_bytes = base64.b64decode(payload.content_base64)
            target_file.write_bytes(raw_bytes)
        elif payload.content_text is not None:
            target_file.write_text(payload.content_text, encoding="utf-8")
        else:
            raise HTTPException(status_code=400, detail="Either content_base64 or content_text must be provided.")

        service = IngestionService()
        result = service.ingest_file(str(target_file), force_reindex=payload.force_reindex)

        return FileIngestResponse(
            status=result["status"],
            document_id=result["document_id"],
            source=result["source"],
            filename=target_file.name,
            chunks_count=result["chunks_count"],
            version=result["version"],
            title=result.get("title"),
            message=f"Successfully uploaded and indexed '{target_file.name}' with {result['chunks_count']} chunk(s).",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error ingesting file payload: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ingest/upload", response_model=FileIngestResponse)
async def upload_and_ingest_file(
    file: UploadFile = File(...),
    category: str = Form("notes"),
    force_reindex: bool = Form(False),
):
    """
    Multipart upload endpoint to upload and immediately index documents:
    supports .doc, .docx, .pdf, .md, .txt, etc.
    """
    try:
        settings = get_settings()
        target_dir = Path(settings.data_dir) / category
        target_dir.mkdir(parents=True, exist_ok=True)

        safe_filename = Path(file.filename).name
        target_file = target_dir / safe_filename

        content = await file.read()
        target_file.write_bytes(content)

        service = IngestionService()
        result = service.ingest_file(str(target_file), force_reindex=force_reindex)

        return FileIngestResponse(
            status=result["status"],
            document_id=result["document_id"],
            source=result["source"],
            filename=safe_filename,
            chunks_count=result["chunks_count"],
            version=result["version"],
            title=result.get("title"),
            message=f"Successfully uploaded and indexed '{safe_filename}' ({result['chunks_count']} chunk(s)).",
        )
    except Exception as e:
        logger.error(f"Error handling file upload {file.filename}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

