import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone

from config.settings import get_settings


class ManifestManager:
    """
    Manages document identity, content hashes, and change detection (NEW, UNCHANGED, MODIFIED, DELETED).
    Prevents duplicate embeddings and ensures idempotent ingestion.
    """

    def __init__(self, manifest_path: Optional[Path] = None):
        settings = get_settings()
        self.manifest_path = manifest_path or (settings.data_dir / ".manifest.json")
        self.state: Dict[str, dict] = self._load()

    def _load(self) -> Dict[str, dict]:
        if not self.manifest_path.exists():
            return {}
        try:
            with open(self.manifest_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def save(self) -> None:
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.manifest_path, "w", encoding="utf-8") as f:
            json.dump(self.state, f, indent=2)

    def check_status(self, document_id: str, content_hash: str) -> str:
        """
        Detect whether a document is NEW, UNCHANGED, or MODIFIED.
        """
        if document_id not in self.state:
            return "NEW"
        record = self.state[document_id]
        if record.get("content_hash") == content_hash:
            return "UNCHANGED"
        return "MODIFIED"

    def get_document_version(self, document_id: str) -> int:
        if document_id in self.state:
            return self.state[document_id].get("version", 1)
        return 1

    def record_document(
        self,
        document_id: str,
        source: str,
        content_hash: str,
        version: int,
        chunk_ids: List[str],
        status: str = "active",
    ) -> None:
        now_iso = datetime.now(timezone.utc).isoformat()
        self.state[document_id] = {
            "document_id": document_id,
            "source": source,
            "content_hash": content_hash,
            "version": version,
            "status": status,
            "chunk_ids": chunk_ids,
            "last_ingested_at": now_iso,
        }
        self.save()

    def detect_deleted(self, active_document_ids: List[str]) -> List[str]:
        """Return list of document_ids in manifest that no longer exist on disk."""
        active_set = set(active_document_ids)
        deleted = [
            doc_id for doc_id, meta in self.state.items()
            if doc_id not in active_set and meta.get("status") != "deleted"
        ]
        return deleted

    def mark_deleted(self, document_id: str) -> None:
        if document_id in self.state:
            self.state[document_id]["status"] = "deleted"
            self.save()
