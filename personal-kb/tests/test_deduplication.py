import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
from ingestion.deduplication import ManifestManager


def test_manifest_deduplication(tmp_path):
    manifest_file = tmp_path / ".manifest.json"
    manager = ManifestManager(manifest_path=manifest_file)

    doc_id = "doc_abc"
    hash_v1 = "hash_111"
    hash_v2 = "hash_222"

    # Step 1: New document
    assert manager.check_status(doc_id, hash_v1) == "NEW"

    # Record v1
    manager.record_document(
        document_id=doc_id,
        source="data/notes/sample.md",
        content_hash=hash_v1,
        version=1,
        chunk_ids=["chunk_1"],
    )

    # Step 2: Unchanged document
    assert manager.check_status(doc_id, hash_v1) == "UNCHANGED"

    # Step 3: Modified document
    assert manager.check_status(doc_id, hash_v2) == "MODIFIED"
    assert manager.get_document_version(doc_id) == 1

    # Record v2
    manager.record_document(
        document_id=doc_id,
        source="data/notes/sample.md",
        content_hash=hash_v2,
        version=2,
        chunk_ids=["chunk_2"],
    )
    assert manager.check_status(doc_id, hash_v2) == "UNCHANGED"
    assert manager.get_document_version(doc_id) == 2
