import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
from llama_index.core.schema import Document
from ingestion.parser import parse_document_into_chunks


def test_multi_decision_chunking():
    text = (
        "# Database Decision\n\n"
        "On March 15, 2026, I decided to use PostgreSQL for production.\n\n"
        "On May 20, 2026, I decided to use SQLite temporarily for the prototype.\n\n"
        "On August 10, 2026, I confirmed that PostgreSQL remains the production database.\n\n"
        "The August decision is the current production decision."
    )
    doc = Document(text=text)
    nodes = parse_document_into_chunks(
        document=doc,
        document_id="doc_test_1",
        source="data/notes/database_decision.md",
        source_type=".md",
        content_hash="dummy_hash",
    )
    assert len(nodes) == 3

    # Check node 0 (March 15)
    assert "March 15, 2026" in nodes[0].text
    assert nodes[0].metadata["status"] == "superseded"
    assert nodes[0].metadata["event_at"].startswith("2026-03-15")
    assert nodes[0].metadata["valid_until"].startswith("2026-05-20")

    # Check node 1 (May 20)
    assert "May 20, 2026" in nodes[1].text
    assert nodes[1].metadata["status"] == "superseded"
    assert nodes[1].metadata["event_at"].startswith("2026-05-20")
    assert nodes[1].metadata["valid_until"].startswith("2026-08-10")

    # Check node 2 (August 10)
    assert "August 10, 2026" in nodes[2].text
    assert nodes[2].metadata["status"] == "active"
    assert nodes[2].metadata["event_at"].startswith("2026-08-10")
    assert nodes[2].metadata["valid_until"] is None


def test_standard_text_chunking():
    text = "This is a simple note without any dated events.\nIt describes background ideas."
    doc = Document(text=text)
    nodes = parse_document_into_chunks(
        document=doc,
        document_id="doc_test_2",
        source="data/notes/simple.md",
        source_type=".md",
        content_hash="dummy_hash2",
    )
    assert len(nodes) >= 1
    assert nodes[0].metadata["status"] == "active"
    assert nodes[0].metadata["event_at"] is None
