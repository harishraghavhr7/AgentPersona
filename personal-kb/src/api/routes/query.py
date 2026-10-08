import logging
import os
import re
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException
from api.schemas import QueryApiRequest, QueryApiResponse
from generation.answer import GenerationService
from ingestion.service import IngestionService, generate_contextual_title_and_filename
from models.query import Citation, QueryType

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Query"])


def format_task_items(text: str) -> str:
    """
    Format unstructured list/todo text into clean markdown task checkboxes.
    Handles hyphen-separated items (e.g. 'complete ml -complete db -practice leetcode'),
    bullets, commas, semicolons, or newlines.
    """
    cleaned = text.strip()
    if re.search(r'-\s+\[[ xX]\]', cleaned):
        return cleaned

    # Split by bullet markers, hyphens between words, or newlines
    # e.g. 'complete ml -complete db -practice leetcode'
    # or '- complete ml \n - complete db'
    parts = re.split(r'(?:\r?\n\s*[-*•]|\s+[-*•]\s*|^[-*•]\s*)', cleaned)
    items = [p.strip() for p in parts if p.strip()]

    if len(items) > 1:
        return "\n".join(f"- [ ] {item}" for item in items)

    # Fallback to comma or semicolon separation if multiple items exist
    if "," in cleaned or ";" in cleaned:
        sub_items = [p.strip() for p in re.split(r"[,;]", cleaned) if p.strip()]
        if len(sub_items) > 1:
            return "\n".join(f"- [ ] {item}" for item in sub_items)

    return f"- [ ] {cleaned}"


def extract_chat_ingestion_payload(query: str) -> Optional[dict]:
    """
    Detect whether the user's chat message is an explicit ingestion instruction
    (e.g., accomplishments, notes, daily tasks, or rules) rather than an informational question.
    """
    raw = query.strip()
    lower = raw.lower()

    # Rule out obvious retrieval questions
    if raw.endswith("?") or lower.startswith((
        "what ", "when ", "where ", "how ", "who ", "which ", "why ",
        "can you", "could you", "show me", "list ", "tell me",
        "is ", "are ", "was ", "were ", "do ", "does ", "did ", "check "
    )):
        return None

    # 1. Accomplishments directive
    # e.g., "my current accomplishments: ...", "current accomplishments: ...", "add accomplishment: ..."
    m = re.match(r"^(?:my\s+)?(?:current\s+)?accomplishments?\s*[:\-]\s*(.+)$", raw, re.IGNORECASE | re.DOTALL)
    if not m:
        m = re.match(r"^(?:add|log|record)\s+(?:to\s+)?(?:my\s+)?accomplishments?\s*[:\-]\s*(.+)$", raw, re.IGNORECASE | re.DOTALL)
    if m:
        content = m.group(1).strip()
        return {
            "text": content,
            "title": "Current Accomplishments",
            "filename": "accomplishments.md",
            "category": "notes",
            "append": True,
        }

    # 2. Rule storage directive
    # e.g., "store rule: ...", "store this rule: ...", "save rule: ...", "project rule: ..."
    m = re.match(r"^(?:store|save|record|add|new)?\s*(?:this\s+)?(?:project\s+)?rules?\s*[:\-]\s*(.+)$", raw, re.IGNORECASE | re.DOTALL)
    if m:
        content = m.group(1).strip()
        return {
            "text": content,
            "title": "Project Rules",
            "filename": "project_rules.md",
            "category": "notes",
            "append": True,
        }

    # 3. Tasks / Today's Lists / Todos
    # e.g., "add today lists - complete ml -complete db -practice leetcode"
    # "add today's list: ...", "today list: ...", "/todo ...", "tasks: ..."
    m = re.match(r"^(?:/(?:todo|todos|task|tasks|list))\s*(?:[:\-]\s*)?(.+)$", raw, re.IGNORECASE | re.DOTALL)
    if not m:
        m = re.match(r"^(?:add\s+)?(?:today(?:\'s)?|daily)\s+(?:lists?|tasks?|todos?|items?)\s*[:\-]\s*(.+)$", raw, re.IGNORECASE | re.DOTALL)
    if not m:
        m = re.match(r"^(?:add\s+)?(?:to\s+(?:today(?:\'s)?\s+)?(?:list|tasks?|todos?)\s*[:\-]\s*)(.+)$", raw, re.IGNORECASE | re.DOTALL)
    if not m:
        m = re.match(r"^(?:add\s+)?(?:tasks?|todos?|to-do|to-dos)\s*[:\-]\s*(.+)$", raw, re.IGNORECASE | re.DOTALL)

    if m:
        content = m.group(1).strip()
        formatted_content = format_task_items(content)
        return {
            "text": formatted_content,
            "title": "Today's Tasks & Lists",
            "filename": "daily_tasks.md",
            "category": "notes",
            "append": True,
            "is_task": True,
        }

    # 4. Explicit Notes / Reminders
    # e.g., "/note ...", "remember: ...", "remember that ...", "note to self: ...", "add note: ..."
    m = re.match(r"^(?:/(?:note|notes|remember|add|ingest))\s*(?:[:\-]\s*)?(.+)$", raw, re.IGNORECASE | re.DOTALL)
    if not m:
        m = re.match(r"^(?:remember(?:\s+that)?|note\s+to\s+self|quick\s+note|new\s+note|take\s+note|add\s+notes?|notes?|save\s+notes?|store\s+notes?)\s*[:\-]?\s*(.+)$", raw, re.IGNORECASE | re.DOTALL)
    if not m:
        m = re.match(r"^(?:add|save|store|record)\s+(?:to\s+(?:my\s+)?(?:notes|knowledge\s*base|kb)\s*[:\-]\s*)(.+)$", raw, re.IGNORECASE | re.DOTALL)
    if not m:
        m = re.match(r"^(?:store|save|record|add)\s*[:\-]\s*(.+)$", raw, re.IGNORECASE | re.DOTALL)

    if m:
        content = m.group(1).strip()
        title, filename = generate_contextual_title_and_filename(content)
        return {
            "text": content,
            "title": title,
            "filename": filename,
            "category": "notes",
            "append": True,
        }

    return None


@router.post("/query", response_model=QueryApiResponse)
def query_knowledge_base(payload: QueryApiRequest):
    try:
        # Check if user message is an ingestion directive (e.g. accomplishments, notes, rules, tasks)
        ingest_payload = extract_chat_ingestion_payload(payload.query)
        if ingest_payload:
            logger.info(f"Detected chat ingestion request: {ingest_payload['title']}")
            ingest_svc = IngestionService()
            res = ingest_svc.ingest_text(
                text=ingest_payload["text"],
                title=ingest_payload.get("title"),
                category=ingest_payload.get("category", "notes"),
                source_name=ingest_payload.get("filename"),
                append=ingest_payload.get("append", True),
            )

            today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            clean_source = res.get("filename") or os.path.basename(res["source"].replace("\\", "/"))
            citation = Citation(
                id=1,
                source=clean_source,
                title=res.get("title") or res["filename"],
                chunk_id=f"{res['document_id']}__c0",
                score=1.0,
                snippet=ingest_payload["text"][:300],
                created_at=today_str,
                document_type="note",
                status="active",
            )

            if ingest_payload.get("is_task"):
                content_display = f"\n\n### Task List\n{ingest_payload['text']}\n"
            else:
                content_display = f"\n\n> **Content:** {ingest_payload['text']}\n"

            answer_text = (
                f"# Knowledge Recorded & Indexed\n\n"
                f"Your knowledge entry has been saved to `{clean_source}` and is now indexed for immediate semantic and temporal retrieval. [1]\n\n"
                f"- **Title:** {res.get('title') or res['filename']}\n"
                f"- **Document:** `{clean_source}`\n"
                f"- **Status:** `{res['status']}` (Version {res['version']})\n"
                f"- **Indexed Chunks:** {res['chunks_count']}"
                f"{content_display}"
            )

            return QueryApiResponse(
                answer=answer_text,
                citations=[citation],
                sources=[citation],
                query_type=QueryType.CURRENT_STATE,
                metadata={
                    "ingested": True,
                    "document_id": res["document_id"],
                    "source": clean_source,
                    "version": res["version"],
                    "chunks_count": res["chunks_count"],
                },
            )

        # Standard RAG Query
        logger.info(f"Processing query: '{payload.query}' (top_k={payload.top_k})")
        service = GenerationService()
        response = service.generate_answer(
            query=payload.query,
            top_k=payload.top_k,
            debug=payload.debug,
        )
        logger.info(f"Query answered successfully. Citations: {len(response.citations)}, Answer length: {len(response.answer)}")
        return QueryApiResponse(
            answer=response.answer,
            citations=response.citations,
            sources=response.sources,
            query_type=response.query_type,
            temporal_filter=response.temporal_filter,
            debug_info=response.debug_info,
            metadata=response.metadata,
        )
    except Exception as e:
        logger.error(f"Error handling /query request: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

