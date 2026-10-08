import base64
from io import BytesIO
from pathlib import Path
import sys
import zipfile
import pytest
from starlette.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from api.main import app
from ingestion.loaders import extract_text_from_binary_doc, extract_text_from_docx, extract_text_from_file


@pytest.fixture
def client():
    return TestClient(app)


def test_docx_and_binary_doc_extraction(tmp_path):
    # 1. Create a minimal valid docx using standard zipfile + XML
    docx_path = tmp_path / "test_rules.docx"
    xml_content = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        '<w:body>'
        '<w:p><w:r><w:t>Rule 1: Always write tests before deploying to production.</w:t></w:r></w:p>'
        '<w:p><w:r><w:t>Rule 2: PostgreSQL is the required database.</w:t></w:r></w:p>'
        '</w:body></w:document>'
    )
    with zipfile.ZipFile(docx_path, "w") as zf:
        zf.writestr("word/document.xml", xml_content)

    extracted_docx = extract_text_from_file(docx_path)
    assert "Rule 1: Always write tests" in extracted_docx
    assert "Rule 2: PostgreSQL" in extracted_docx

    # 2. Create a legacy binary .doc file
    doc_path = tmp_path / "attachedrules.doc"
    doc_bytes = b"\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1" + b"\x00" * 20 + b"Upcoming Project Rule: Mandatory code reviews on all PRs.\x00\x00"
    doc_path.write_bytes(doc_bytes)

    extracted_doc = extract_text_from_file(doc_path)
    assert "Upcoming Project Rule: Mandatory code reviews" in extracted_doc


def test_ingest_text_api(client):
    response = client.post(
        "/ingest/text",
        json={
            "text": "Completed the RAG pipeline with Groq, Gemini and OpenRouter fallback chain.",
            "title": "My Accomplishments",
            "category": "notes",
            "filename": "accomplishments.md",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["NEW", "MODIFIED", "UNCHANGED"]
    assert data["chunks_count"] >= 1
    assert "accomplishments.md" in data["source"]
    assert "indexed" in data["message"].lower()


def test_chat_directive_ingest_accomplishments(client):
    response = client.post(
        "/query",
        json={"query": "my current accomplishments: Built automated multi-format ingestion for docx, doc, pdf and markdown."},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["metadata"].get("ingested") is True
    assert len(data["citations"]) >= 1
    assert "accomplishments.md" in data["citations"][0]["source"]
    assert "Knowledge Recorded & Indexed" in data["answer"]


def test_chat_directive_ingest_today_lists(client):
    # Tests the user's exact input format
    response = client.post(
        "/query",
        json={"query": "add today lists - complete ml -complete db -practice leetcode"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["metadata"].get("ingested") is True
    assert len(data["citations"]) >= 1
    assert "daily_tasks.md" in data["citations"][0]["source"]
    assert "Knowledge Recorded & Indexed" in data["answer"]
    assert "- [ ] complete ml" in data["answer"]
    assert "- [ ] complete db" in data["answer"]
    assert "- [ ] practice leetcode" in data["answer"]


def test_chat_directive_ingest_slash_todo(client):
    response = client.post(
        "/query",
        json={"query": "/todo deploy staging server - run integration tests"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["metadata"].get("ingested") is True
    assert len(data["citations"]) >= 1
    assert "daily_tasks.md" in data["citations"][0]["source"]
    assert "- [ ] deploy staging server" in data["answer"]


def test_chat_directive_ingest_note(client):
    response = client.post(
        "/query",
        json={"query": "remember that the security audit is scheduled for October 15"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["metadata"].get("ingested") is True
    assert len(data["citations"]) >= 1
    assert "security_audit_scheduled_october_15.md" in data["citations"][0]["source"]
    assert "Knowledge Recorded & Indexed" in data["answer"]


def test_chat_directive_ingest_rules(client):
    response = client.post(
        "/query",
        json={"query": "store this rule: All microservices must use gRPC for internal RPC and REST for external APIs."},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["metadata"].get("ingested") is True
    assert len(data["citations"]) >= 1
    assert "project_rules.md" in data["citations"][0]["source"]
    assert "Knowledge Recorded & Indexed" in data["answer"]


def test_file_json_ingest(client):
    text_payload = "# Upcoming Project Rules\n\n- Rule 1: Zero downtime deployments\n- Rule 2: PostgreSQL for all persistent state\n"
    response = client.post(
        "/ingest/file",
        json={
            "filename": "test_attached_rules.md",
            "content_text": text_payload,
            "category": "notes",
            "force_reindex": True,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "test_attached_rules.md"
    assert data["chunks_count"] >= 1


def test_file_multipart_upload(client):
    file_bytes = b"Upcoming Project Architecture: Event-driven architecture with Kafka."
    response = client.post(
        "/ingest/upload",
        files={"file": ("test_project_arch.txt", file_bytes, "text/plain")},
        data={"category": "notes", "force_reindex": "true"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "test_project_arch.txt"
    assert data["chunks_count"] >= 1


def test_immediate_retrieval_of_ingested_knowledge(client):
    # Query for the rule that was just ingested
    response = client.post(
        "/query",
        json={"query": "What database is required according to the upcoming project rules?"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert len(data["citations"]) >= 1
    # Check that citations link to the newly ingested rule document
    sources = [c["source"] for c in data["citations"]]
    assert any("test_attached_rules.md" in s or "project_rules.md" in s or "database_decision.md" in s for s in sources)
