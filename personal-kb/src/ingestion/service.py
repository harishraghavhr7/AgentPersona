from datetime import datetime, timezone
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from qdrant_client.http.models import Filter, FieldCondition, MatchValue

from config.settings import get_settings
from models.document import generate_stable_document_id, compute_content_hash
from models.metadata import format_rfc3339, SourceType
from storage.qdrant import get_qdrant_client, ensure_collection_and_indexes
from llama_index.core.schema import Document
from .loaders import load_from_directory, load_single_file
from .parser import parse_document_into_chunks
from .deduplication import ManifestManager
from .pipeline import run_node_ingestion

logger = logging.getLogger(__name__)


class IngestionService:
    """
    Orchestrates idempotent document ingestion, change detection,
    temporal parsing, versioning, embedding, and vector storage.
    """

    def __init__(self):
        self.settings = get_settings()
        self.client = get_qdrant_client()
        self.manifest = ManifestManager()
        raw_coll = self.settings.qdrant_collection
        self.collection_name = (raw_coll or "").strip().strip('"').strip("'") or "personal_knowledge"
        ensure_collection_and_indexes(self.client, self.collection_name)

    def ingest_file(
        self,
        file_path: str,
        force_reindex: bool = False,
    ) -> Dict[str, Any]:
        """
        Ingest or update a single file into the knowledge base.
        Performs change detection, temporal parsing, versioning, embeddings, and vector storage.
        """
        target = Path(file_path).resolve()
        if not target.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        try:
            rel_source = str(target.relative_to(Path.cwd()))
        except Exception:
            rel_source = str(target)

        raw_docs = load_single_file(str(target))
        if not raw_docs:
            return {
                "status": "SKIPPED",
                "document_id": generate_stable_document_id(rel_source),
                "source": rel_source,
                "chunks_count": 0,
                "version": 0,
            }

        # Combine text from docs if multiple fragments
        combined_text = "\n\n".join([d.text for d in raw_docs if d.text])
        doc_id = generate_stable_document_id(rel_source)
        content_hash = compute_content_hash(combined_text)
        src_type = target.suffix.lower()

        status = "NEW" if force_reindex else self.manifest.check_status(doc_id, content_hash)
        if status == "UNCHANGED":
            # Reconcile: verify that the document's active points actually exist in Qdrant
            try:
                active_pts = self.client.count(
                    collection_name=self.collection_name,
                    count_filter=Filter(
                        must=[
                            FieldCondition(key="document_id", match=MatchValue(value=doc_id)),
                            FieldCondition(key="status", match=MatchValue(value="active")),
                        ]
                    ),
                    exact=True,
                ).count
                if active_pts == 0:
                    logger.info(f"Document '{rel_source}' is in manifest but missing from Qdrant. Re-indexing...")
                    status = "NEW"
            except Exception as e:
                logger.debug(f"Could not verify Qdrant point count for {rel_source}: {e}")

        if status == "UNCHANGED":
            logger.debug(f"Document unchanged, skipping: {rel_source}")
            existing_meta = self.manifest.state.get(doc_id, {})
            return {
                "status": "UNCHANGED",
                "document_id": doc_id,
                "source": rel_source,
                "chunks_count": len(existing_meta.get("chunk_ids", [])),
                "version": existing_meta.get("version", 1),
                "title": target.stem.replace("_", " ").title(),
            }

        now = datetime.now(timezone.utc)
        now_rfc = format_rfc3339(now)

        if status == "MODIFIED":
            logger.info(f"Document modified: {rel_source}. Transitioning old version to superseded.")
            prev_version = self.manifest.get_document_version(doc_id)
            new_version = prev_version + 1

            # Update prior chunks in Qdrant to superseded
            try:
                self.client.set_payload(
                    collection_name=self.collection_name,
                    payload={"status": "superseded", "valid_until": now_rfc},
                    points=Filter(
                        must=[
                            FieldCondition(key="document_id", match=MatchValue(value=doc_id)),
                            FieldCondition(key="status", match=MatchValue(value="active")),
                        ]
                    ),
                    wait=True,
                )
            except Exception as e:
                logger.warning(f"Error marking prior version superseded in Qdrant: {e}")
        else:
            new_version = 1

        primary_doc = Document(text=combined_text, metadata=dict(raw_docs[0].metadata))

        # Parse into temporal chunks
        nodes = parse_document_into_chunks(
            document=primary_doc,
            document_id=doc_id,
            source=rel_source,
            source_type=src_type,
            content_hash=content_hash,
            title=target.stem.replace("_", " ").title(),
            chunk_size=self.settings.chunk_size,
            chunk_overlap=self.settings.chunk_overlap,
        )

        # Set version on all generated nodes
        for n in nodes:
            n.metadata["version"] = new_version

        # Run embeddings and store in Qdrant
        run_node_ingestion(nodes)

        # Record in manifest
        chunk_ids = [n.id_ for n in nodes]
        self.manifest.record_document(
            document_id=doc_id,
            source=rel_source,
            content_hash=content_hash,
            version=new_version,
            chunk_ids=chunk_ids,
            status="active",
        )

        return {
            "status": status,
            "document_id": doc_id,
            "source": rel_source,
            "chunks_count": len(nodes),
            "version": new_version,
            "title": target.stem.replace("_", " ").title(),
        }

    def ingest_text(
        self,
        text: str,
        title: Optional[str] = None,
        category: str = "notes",
        source_name: Optional[str] = None,
        event_at: Optional[str] = None,
        append: bool = False,
    ) -> Dict[str, Any]:
        """
        Ingest text content directly (e.g. from chat, notes, accomplishments, or rules).
        Saves to the knowledge base data directory and indexes immediately into Qdrant.
        """
        target_dir = Path(self.settings.data_dir) / category
        target_dir.mkdir(parents=True, exist_ok=True)

        import re
        if source_name:
            fname = Path(source_name).name
            if not any(fname.lower().endswith(ext) for ext in [".md", ".markdown", ".txt"]):
                fname += ".md"
        elif title:
            slug = re.sub(r"[^a-zA-Z0-9_-]", "_", title.lower()).strip("_")
            fname = f"{slug}.md"
        else:
            lower = text.lower()
            if any(k in lower for k in ["accomplishment", "achieved", "completed", "milestone"]):
                fname = "accomplishments.md"
            elif any(k in lower for k in ["rule", "guideline", "standard", "policy"]):
                fname = "project_rules.md"
            elif any(k in lower for k in ["task", "todo", "today list", "daily list"]):
                fname = "daily_tasks.md"
            else:
                now_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
                fname = f"note_{now_str}.md"

        file_path = target_dir / fname
        date_str = event_at or datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # Determine whether to append or create new
        appendable_files = ["accomplishments.md", "project_rules.md", "daily_tasks.md", "chat_notes.md"]
        if file_path.exists() and (append or fname in appendable_files):
            section_title = title or f"Update ({date_str})"
            append_text = f"\n\n## {section_title} - {date_str}\n\n{text.strip()}\n"
            with open(file_path, "a", encoding="utf-8") as f:
                f.write(append_text)
        else:
            doc_title = title or fname.replace(".md", "").replace("_", " ").title()
            initial_content = f"# {doc_title}\n\n**Date:** {date_str}\n\n## {doc_title} - {date_str}\n\n{text.strip()}\n"
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(initial_content)

        res = self.ingest_file(str(file_path), force_reindex=False)
        res["file_path"] = str(file_path)
        res["filename"] = fname
        return res

    def ingest_directory(
        self,
        directory_path: Optional[str] = None,
        force_reindex: bool = False,
    ) -> Dict[str, Any]:
        """
        Scan and ingest documents from directory.
        Detects NEW, UNCHANGED, and MODIFIED documents.
        """
        from .loaders import get_supported_extensions
        target_dir = Path(directory_path or self.settings.data_dir)
        if not target_dir.exists():
            target_dir.mkdir(parents=True, exist_ok=True)
            return {"processed": 0, "added": 0, "updated": 0, "skipped": 0, "failed": 0}

        supported_exts = set(get_supported_extensions())
        active_doc_ids = []
        processed = 0
        added = 0
        updated = 0
        skipped = 0
        failed = 0

        for item in target_dir.glob("**/*"):
            if item.is_file() and item.suffix.lower() in supported_exts:
                processed += 1
                try:
                    res = self.ingest_file(str(item), force_reindex=force_reindex)
                    active_doc_ids.append(res["document_id"])
                    if res["status"] == "NEW":
                        added += 1
                    elif res["status"] == "MODIFIED":
                        updated += 1
                    elif res["status"] == "UNCHANGED":
                        skipped += 1
                except Exception as e:
                    logger.error(f"Failed to ingest {item}: {e}", exc_info=True)
                    failed += 1

        # Check for deleted documents
        deleted_ids = self.manifest.detect_deleted(active_doc_ids)
        for d_id in deleted_ids:
            logger.info(f"Document deleted from storage: {d_id}. Archiving in Qdrant.")
            try:
                self.client.set_payload(
                    collection_name=self.collection_name,
                    payload={"status": "archived"},
                    points=Filter(must=[FieldCondition(key="document_id", match=MatchValue(value=d_id))]),
                    wait=True,
                )
                self.manifest.mark_deleted(d_id)
            except Exception as e:
                logger.warning(f"Error archiving deleted document {d_id} in Qdrant: {e}")

        return {
            "processed": processed,
            "added": added,
            "updated": updated,
            "skipped": skipped,
            "failed": failed,
        }
